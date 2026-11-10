/** A played word flies from the bomb to the list of played words (transform and opacity only). */
export function flyWord(text: string, from: DOMRect, to: DOMRect): void {
	if (typeof document === 'undefined') return;
	if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
	const el = document.createElement('div');
	el.textContent = text;
	Object.assign(el.style, {
		position: 'fixed',
		left: `${from.left + from.width / 2}px`,
		top: `${from.top + from.height / 2}px`,
		zIndex: '55',
		pointerEvents: 'none',
		padding: '0.15rem 0.8rem 0.3rem',
		background: 'var(--matcha)',
		color: 'var(--sumi)',
		border: '3px solid var(--sumi)',
		borderRadius: '12px',
		boxShadow: '3px 4px 0 var(--sumi)',
		fontFamily: 'var(--font-kana)',
		fontWeight: '700',
		fontSize: '1.5rem',
		whiteSpace: 'nowrap',
		willChange: 'transform, opacity'
	});
	document.body.appendChild(el);
	const dx = to.left + to.width / 2 - (from.left + from.width / 2);
	const dy = to.top + to.height / 2 - (from.top + from.height / 2);
	const animation = el.animate(
		[
			{ transform: 'translate(-50%, -50%) scale(0.6)', opacity: 0 },
			{ transform: 'translate(-50%, -50%) scale(1.15)', opacity: 1, offset: 0.25 },
			{
				transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(0.55)`,
				opacity: 0.2
			}
		],
		{ duration: 520, easing: 'cubic-bezier(0.3, 0.7, 0.3, 1)' }
	);
	animation.onfinish = () => el.remove();
}

/** Short screen shake for explosions. */
export function shake(el: HTMLElement | undefined): void {
	if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
	el.animate(
		[
			{ transform: 'translate(0, 0)' },
			{ transform: 'translate(-7px, 4px)' },
			{ transform: 'translate(6px, -5px)' },
			{ transform: 'translate(-4px, -3px)' },
			{ transform: 'translate(3px, 3px)' },
			{ transform: 'translate(0, 0)' }
		],
		{ duration: 280, easing: 'ease-out' }
	);
}
