-- What is happening in the game, from the finished games stored in PostgreSQL.
-- Run on the server:  ./stats.sh        (or:  ./stats.sh --days 30)
-- Only aggregates are printed. A "player" is a browser (its random guest id), not a person: someone who clears
-- their browser data, or plays on two devices, counts twice. CPU players are never counted.
\set QUIET on
\pset border 2
\pset null '-'
\if :{?days}
\else
  \set days 14
\endif

\echo
\echo '=== Overview'
select count(*)                                                      as games_total,
       count(*) filter (where ended_at > now() - interval '24 hours') as games_24h,
       count(*) filter (where ended_at > now() - interval '7 days')   as games_7d,
       round(avg(duration_ms) / 1000.0)                               as avg_duration_s,
       round(avg(players_count), 1)                                   as avg_players,
       (select count(distinct guest_id) from game_players)            as players_total,
       (select count(distinct gp.guest_id) from game_players gp join games g on g.id = gp.game_id
         where g.ended_at > now() - interval '7 days')                as players_7d
from games;

\echo
\echo '=== Games and distinct players per day'
select d::date as day,
       count(distinct g.id)         as games,
       count(distinct gp.guest_id)  as players
from generate_series(current_date - (:days - 1), current_date, interval '1 day') d
left join games g on g.ended_at::date = d::date
left join game_players gp on gp.game_id = g.id and not gp.is_bot
group by 1 order by 1 desc;

\echo
\echo '=== Modes'
select kind as game, mode, count(*) as games, round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from games group by kind, mode order by games desc;

\echo
\echo '=== Interface languages (human players, one count per game played)'
select coalesce(lang, 'unknown') as lang, count(*) as player_games,
       round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from game_players where not is_bot group by 1 order by 2 desc;

\echo
\echo '=== Players by number of games played'
select case when n = 1 then '1 game' when n < 5 then '2-4 games' when n < 20 then '5-19 games' else '20+ games' end as played,
       count(*) as players
from (select guest_id, count(*) as n from game_players where guest_id is not null group by 1) t
group by 1 order by min(n);

\echo
\echo '=== Players who came back on another day'
select count(*) filter (where days >= 2) as came_back, count(*) as players,
       round(100.0 * count(*) filter (where days >= 2) / nullif(count(*), 0), 1) as pct
from (select gp.guest_id, count(distinct g.ended_at::date) as days
      from game_players gp join games g on g.id = gp.game_id
      where gp.guest_id is not null group by 1) t;

\echo
\echo '=== Turns: how often the bomb wins, and how fast players answer'
select count(*)                                                       as turns,
       round(100.0 * count(*) filter (where outcome <> 'word') / count(*), 1) as explosion_pct,
       round(avg(response_ms) filter (where outcome = 'word'))        as avg_answer_ms,
       round(avg(rejected_attempts), 2)                               as avg_refused_words_per_turn
from bomb_turns;

\echo
\echo '=== Prompt length vs difficulty'
select char_length(fragment) as kana, count(*) as turns,
       round(100.0 * count(*) filter (where outcome <> 'word') / count(*), 1) as explosion_pct,
       round(avg(response_ms) filter (where outcome = 'word')) as avg_answer_ms
from bomb_turns group by 1 order by 1;

\echo
\echo '=== Hardest prompts (at least 20 turns)'
select fragment, count(*) as turns,
       round(100.0 * count(*) filter (where outcome <> 'word') / count(*), 1) as explosion_pct,
       round(avg(response_ms) filter (where outcome = 'word')) as avg_answer_ms
from bomb_turns group by fragment having count(*) >= 20
order by explosion_pct desc, turns desc limit 15;

\echo
\echo '=== Most played words'
select word, count(*) as times from bomb_turns where outcome = 'word' and word <> ''
group by word order by times desc, word limit 15;

\echo
\echo '=== Accounts and their ages (from the date of birth asked at sign-up)'
select count(*)                                                       as accounts,
       count(birth_date)                                              as with_birth_date,
       round(avg(date_part('year', age(birth_date)))::numeric, 1)     as avg_age,
       min(date_part('year', age(birth_date)))                        as youngest,
       max(date_part('year', age(birth_date)))                        as oldest
from accounts;

select case
         when a < 13 then '1. under 13'
         when a < 18 then '2. 13 to 17'
         when a < 25 then '3. 18 to 24'
         when a < 35 then '4. 25 to 34'
         when a < 45 then '5. 35 to 44'
         else '6. 45 and over'
       end                                                            as age_group,
       count(*)                                                       as accounts
from (select date_part('year', age(birth_date)) as a from accounts where birth_date is not null) ages
group by 1 order by 1;
