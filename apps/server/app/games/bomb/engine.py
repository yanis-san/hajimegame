"""Pure, deterministic bomb game engine with three modes.

No network, no database, no system clock. Clock and RNG are injected: the same seed and the same
actions always produce the same game.

Modes
- ``classic``: a fragment of 1 to 3 kana is shown, the word must contain it. The fragment difficulty adapts
  to each player's answer speed: fast answers get rarer fragments, slow answers or explosions easier ones.
- ``shiritori``: the word must START with the last kana of the previous word.
  A word ending in ん is refused (or, with n_penalty, costs a life). The chain survives explosions.
- ``kanji``: a kanji of the chosen JLPT levels is shown; the word must be written with it (typed in kanji, or
  in kana when the dictionary writes that word with the kanji). The "fragment" of the turn is the kanji.

Timing rule (documented in docs/PROTOCOL.md): a word received at ``at <= deadline`` is judged on its merits;
``at > deadline`` is ``too_late`` and the bomb explodes. A ``timeout`` before the deadline is ignored.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from app.games.base import Clock, GameEvent, Phase, PlayerInfo
from app.games.bomb import events as ev
from app.games.bomb.ports import FragmentPicker, KanjiSource, WordValidator
from app.games.bomb.settings import LIFE_CAP, BombSettings
from app.japanese.kana import shiritori_end, units

RECENT_FRAGMENTS = 8
BONUS_LIST_SIZE = 3
# The 45 basic hiragana used for bonus lives (gojuon without を).
BONUS_POOL = tuple(
    "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわん"
)

# Adaptive difficulty: share of the fuse used to answer.
FAST_RATIO = 0.30
SLOW_RATIO = 0.65
SKILL_MIN, SKILL_START, SKILL_MAX = 0, 1, 2
# A shiritori chain never continues with a kana that starts fewer words than this.
MIN_START_WORDS = 20
_BAD_STARTS = "んーっゃゅょぁぃぅぇぉゎを"


@dataclass(slots=True)
class PlayerState:
    info: PlayerInfo
    lives: int
    alive: bool = True
    score: int = 0
    words: int = 0
    skill: int = SKILL_START  # 0 easy fragments, 2 hard fragments (classic mode)
    bonus_left: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class PlayedWord:
    turn: int
    player_id: str
    word: str
    reading: str
    entry_id: int


class BombEngine:
    def __init__(
        self,
        players: Sequence[PlayerInfo],
        settings: BombSettings,
        *,
        validator: WordValidator,
        fragments: FragmentPicker,
        clock: Clock,
        rng: random.Random,
        kanji: KanjiSource | None = None,
    ) -> None:
        ids = [p.id for p in players]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate player ids")
        if not 2 <= len(players) <= settings.max_players:
            raise ValueError("player count out of range")
        if settings.mode == "kanji" and kanji is None:
            raise ValueError("the kanji mode needs a kanji source")
        self.settings = settings
        self._kanji = kanji
        self._validator = validator
        self._fragments = fragments
        self._clock = clock
        self._rng = rng
        self._players: dict[str, PlayerState] = {p.id: PlayerState(p, settings.lives) for p in players}
        self._order = tuple(ids)
        self._phase = Phase.PLAYING
        self._started = False
        self._turn = 0
        self._current: str | None = None
        self._fragment = ""
        self._deadline: float | None = None
        self._turn_started = 0.0
        self._next_start = ""  # shiritori: the kana the next word must start with
        self._recent: list[str] = []
        self._used: set[int] = set()
        self._history: list[PlayedWord] = []
        self._eliminated: list[str] = []  # in order of elimination
        self._winner: str | None = None

    # ------------------------------------------------------------------ read-only view

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def next_deadline(self) -> float | None:
        return self._deadline if self._phase is Phase.PLAYING else None

    @property
    def turn(self) -> int:
        return self._turn

    @property
    def current_player(self) -> str | None:
        return self._current

    @property
    def fragment(self) -> str:
        return self._fragment

    @property
    def winner(self) -> str | None:
        return self._winner

    @property
    def players(self) -> tuple[PlayerState, ...]:
        return tuple(self._players[i] for i in self._order)

    @property
    def used_entry_ids(self) -> frozenset[int]:
        return frozenset(self._used)

    @property
    def history(self) -> tuple[PlayedWord, ...]:
        return tuple(self._history)

    def alive_ids(self) -> list[str]:
        return [i for i in self._order if self._players[i].alive]

    def ranking(self) -> tuple[str, ...]:
        """Best first: winner, then players in reverse order of elimination."""
        alive = self.alive_ids()
        return (*alive, *reversed(self._eliminated))

    # ------------------------------------------------------------------ actions

    def start(self) -> list[GameEvent]:
        if self._started:
            raise RuntimeError("game already started")
        self._started = True
        if self.settings.bonus_kana:
            for state in self._players.values():
                state.bonus_left = set(self._rng.sample(BONUS_POOL, BONUS_LIST_SIZE))
        out: list[GameEvent] = [ev.GameStarted(player_ids=self._order, lives=self.settings.lives)]
        first = self._order[self._rng.randrange(len(self._order))]
        self._begin_turn(first, out)
        return out

    def submit(self, player_id: str, text: str, at: float | None = None) -> list[GameEvent]:
        if self._phase is not Phase.PLAYING or self._current is None or self._deadline is None:
            return []
        now = self._clock.now() if at is None else at
        out: list[GameEvent] = []
        if player_id != self._current:
            if player_id in self._players:
                out.append(
                    ev.WordRejected(turn=self._turn, player_id=player_id, text=text, reason="not_your_turn")
                )
            return out
        if now > self._deadline:
            out.append(ev.WordRejected(turn=self._turn, player_id=player_id, text=text, reason="too_late"))
            self._explode(out)
            return out

        shiritori = self.settings.mode == "shiritori"
        if self._kanji is not None and self.settings.mode == "kanji":
            hits = self._kanji.matches(text, self._fragment)
        else:
            hits = self._validator.matches(text, self._fragment, starts_with=shiritori)
        if not hits:
            if self._kanji is not None and self.settings.mode == "kanji":
                reason = self._kanji.reject_reason(text, self._fragment)
            else:
                reason = self._validator.reject_reason(text, self._fragment, starts_with=shiritori)
            out.append(ev.WordRejected(turn=self._turn, player_id=player_id, text=text, reason=reason))
            return out
        hit = next((h for h in hits if h.entry_id not in self._used), None)
        if hit is None:
            out.append(
                ev.WordRejected(turn=self._turn, player_id=player_id, text=text, reason="already_used")
            )
            return out
        ending = shiritori_end(hit.reading) if shiritori else ""
        n_ending = shiritori and ending == "ん"
        if n_ending and not self.settings.n_penalty:
            out.append(ev.WordRejected(turn=self._turn, player_id=player_id, text=text, reason="ends_with_n"))
            return out

        state = self._players[player_id]
        self._used.add(hit.entry_id)
        gain = len(units(hit.reading))
        state.score += gain
        state.words += 1
        self._history.append(PlayedWord(self._turn, player_id, hit.text, hit.reading, hit.entry_id))
        out.append(
            ev.WordAccepted(
                turn=self._turn,
                player_id=player_id,
                word=hit.text,
                reading=hit.reading,
                score_gain=gain,
                score=state.score,
                meaning_fr=hit.meaning_fr,
                meaning_en=hit.meaning_en,
                example_ja=hit.example_ja,
                example_en=hit.example_en,
                example_fr=hit.example_fr,
            )
        )
        self._adapt(state, (now - self._turn_started) / max(1e-9, self.settings.fuse_seconds))
        if shiritori:
            enough = self._validator.start_count(ending) >= MIN_START_WORDS
            self._next_start = ending if enough and not n_ending else ""
        self._update_bonus(state, hit.reading, out)
        if n_ending:  # the word counts, but ending on ん costs a life
            self._explode(out, "n_ending")
            return out
        self._begin_turn(self._next_alive(player_id), out)
        return out

    def timeout(self, at: float | None = None, turn: int | None = None) -> list[GameEvent]:
        if self._phase is not Phase.PLAYING or self._deadline is None:
            return []
        if turn is not None and turn != self._turn:
            return []
        now = self._clock.now() if at is None else at
        if now < self._deadline:
            return []
        out: list[GameEvent] = []
        self._explode(out)
        return out

    def leave(self, player_id: str, at: float | None = None) -> list[GameEvent]:
        state = self._players.get(player_id)
        if state is None or not state.alive or self._phase is not Phase.PLAYING:
            return []
        out: list[GameEvent] = []
        was_current = player_id == self._current
        successor = self._next_alive(player_id) if was_current else None
        self._eliminate(state, "left", out)
        if self._phase is Phase.PLAYING and was_current and successor is not None:
            self._begin_turn(successor, out)
        return out

    # ------------------------------------------------------------------ internals

    def _next_alive(self, after: str) -> str:
        start = self._order.index(after)
        for step in range(1, len(self._order) + 1):
            candidate = self._order[(start + step) % len(self._order)]
            if self._players[candidate].alive:
                return candidate
        return after

    @staticmethod
    def _adapt(state: PlayerState, ratio: float) -> None:
        """Answer speed drives difficulty: fast answers earn harder fragments, slow ones easier."""
        if ratio < FAST_RATIO:
            state.skill = min(SKILL_MAX, state.skill + 1)
        elif ratio > SLOW_RATIO:
            state.skill = max(SKILL_MIN, state.skill - 1)

    def _pick_fragment(self, state: PlayerState) -> str:
        if self.settings.mode == "kanji":
            assert self._kanji is not None
            return self._kanji.draw(self.settings.levels, self._rng, self._recent)
        if self.settings.mode == "classic":
            return self._fragments.pick_text(self._rng, state.skill, self._recent)
        if self._next_start:
            return self._next_start
        # Opening of a shiritori chain (or a dead end): a common kana that many words start with.
        for _ in range(30):
            first = self._fragments.pick_text(self._rng, 0, self._recent)[0]
            if first not in _BAD_STARTS and self._validator.start_count(first) >= MIN_START_WORDS:
                return first
        return "あ"

    def _begin_turn(self, player_id: str, out: list[GameEvent]) -> None:
        self._turn += 1
        fragment = self._pick_fragment(self._players[player_id])
        self._recent.append(fragment)
        del self._recent[:-RECENT_FRAGMENTS]
        fuse = self.settings.fuse_seconds
        self._current = player_id
        self._fragment = fragment
        self._turn_started = self._clock.now()
        self._deadline = self._turn_started + fuse
        out.append(
            ev.TurnStarted(
                turn=self._turn,
                player_id=player_id,
                fragment=fragment,
                deadline=self._deadline,
                fuse_seconds=fuse,
            )
        )

    def _explode(self, out: list[GameEvent], cause: Literal["timeout", "n_ending"] = "timeout") -> None:
        assert self._current is not None
        player_id = self._current
        state = self._players[player_id]
        state.lives -= 1
        state.skill = SKILL_MIN  # the next fragment will be an easy one
        out.append(ev.Explosion(turn=self._turn, player_id=player_id, lives=state.lives, cause=cause))
        successor = self._next_alive(player_id)
        if state.lives <= 0:
            self._eliminate(state, "explosion", out)
            if self._phase is not Phase.PLAYING:
                return
        self._begin_turn(successor, out)

    def _eliminate(
        self, state: PlayerState, reason: Literal["explosion", "left"], out: list[GameEvent]
    ) -> None:
        state.alive = False
        state.lives = max(0, state.lives)
        self._eliminated.append(state.info.id)
        place = len(self.alive_ids()) + 1
        out.append(ev.PlayerEliminated(player_id=state.info.id, place=place, reason=reason))
        alive = self.alive_ids()
        if len(alive) <= 1:
            self._finish(out)

    def _finish(self, out: list[GameEvent]) -> None:
        alive = self.alive_ids()
        self._phase = Phase.FINISHED
        self._winner = alive[0] if alive else None
        self._current = None
        self._deadline = None
        out.append(ev.GameOver(winner_id=self._winner, ranking=self.ranking()))

    def _update_bonus(self, state: PlayerState, reading: str, out: list[GameEvent]) -> None:
        if not self.settings.bonus_kana or not state.bonus_left:
            return
        used = {k for k in state.bonus_left if k in reading}
        if not used:
            return
        state.bonus_left -= used
        if state.bonus_left:
            out.append(ev.BonusProgress(player_id=state.info.id, remaining=tuple(sorted(state.bonus_left))))
            return
        if state.lives < LIFE_CAP:
            state.lives += 1
            out.append(ev.LifeGained(player_id=state.info.id, lives=state.lives))
        state.bonus_left = set(self._rng.sample(BONUS_POOL, BONUS_LIST_SIZE))
        out.append(ev.BonusProgress(player_id=state.info.id, remaining=tuple(sorted(state.bonus_left))))
