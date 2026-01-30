<script lang="ts">
	interface Option {
		value: number;
		label: string;
	}

	interface Props {
		options: Option[];
		selected: number[];
		placeholder?: string;
		onchange: (selected: number[]) => void;
	}

	let { options, selected, placeholder = 'Select...', onchange }: Props = $props();

	let open = $state(false);
	let triggerElement: HTMLButtonElement | null = $state(null);
	let dropdownElement: HTMLDivElement | null = $state(null);

	const displayText = $derived(() => {
		if (selected.length === 0) return placeholder;
		if (selected.length <= 2) {
			return options
				.filter((o) => selected.includes(o.value))
				.map((o) => o.label)
				.join(', ');
		}
		return `${selected.length} selected`;
	});

	function toggle(value: number) {
		if (selected.includes(value)) {
			onchange(selected.filter((v) => v !== value));
		} else {
			onchange([...selected, value]);
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			open = false;
			triggerElement?.focus();
		}
	}

	function handleClickOutside(event: MouseEvent) {
		if (
			open &&
			triggerElement &&
			dropdownElement &&
			!triggerElement.contains(event.target as Node) &&
			!dropdownElement.contains(event.target as Node)
		) {
			open = false;
		}
	}

	$effect(() => {
		if (open) {
			document.addEventListener('click', handleClickOutside);
			document.addEventListener('keydown', handleKeydown);
			return () => {
				document.removeEventListener('click', handleClickOutside);
				document.removeEventListener('keydown', handleKeydown);
			};
		}
	});
</script>

<div class="relative">
	<button
		bind:this={triggerElement}
		type="button"
		class="flex min-w-32 items-center justify-between gap-2 rounded border-2 border-secondary-950 bg-black px-3 py-2 text-sm text-white hover:border-primary-800 focus:border-primary-800 focus:outline-none"
		onclick={() => (open = !open)}
		onkeydown={handleKeydown}
	>
		<span class={selected.length === 0 ? 'text-surface-400' : ''}>{displayText()}</span>
		<svg
			class="h-4 w-4 text-surface-400 transition-transform {open ? 'rotate-180' : ''}"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	{#if open}
		<div
			bind:this={dropdownElement}
			class="absolute top-full z-50 mt-1 max-h-60 min-w-full overflow-auto rounded bg-black/90 shadow-xl backdrop-blur-sm"
		>
			{#each options as option (option.value)}
				<label class="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-primary-950/60">
					<input
						type="checkbox"
						checked={selected.includes(option.value)}
						onchange={() => toggle(option.value)}
						class="rounded"
					/>
					<span class="text-sm text-white">{option.label}</span>
				</label>
			{/each}
		</div>
	{/if}
</div>
