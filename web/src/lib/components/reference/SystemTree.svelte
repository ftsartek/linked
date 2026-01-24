<script lang="ts">
	import { classColour, effectColour } from '$lib/helpers/renderClass';
	import type { WormholeRegion, WormholeSystemStatic } from './wormholeConstants';

	interface Props {
		regions: WormholeRegion[];
	}

	let { regions }: Props = $props();

	// Drifter wormhole classes (Sentinel, Barbican, Vidette, Redoubt, Conflux)
	const DRIFTER_CLASSES = ['Sentinel', 'Barbican', 'Vidette', 'Redoubt', 'Conflux'];

	function getDisplayClass(className: string): string {
		if (DRIFTER_CLASSES.includes(className)) {
			return 'drifter';
		}
		return className.toLowerCase();
	}
</script>

{#snippet staticDisplay(statics: WormholeSystemStatic[])}
	{#each statics as s (s.id)}
		<span class={classColour(s.target_name)}>{s.target_name.toLowerCase()}</span>
		<span class="text-surface-500"></span>
	{/each}
{/snippet}

<div class="font-mono text-sm">
	{#each regions as region (region.id)}
		<div class="mb-8">
			<!-- Region with constellations -->
			<div class="flex">
				<!-- Region label (vertical, rotated) -->
				<div class="relative mr-1 flex w-8 shrink-0 items-start justify-center pt-2">
					<div class="absolute top-0 left-0 h-full w-px bg-surface-700"></div>
					<span
						class="text-surface-500"
						style="writing-mode: vertical-rl; transform: rotate(180deg); font-size: 11px;"
					>
						{region.name}
					</span>
				</div>

				<!-- Constellations column -->
				<div class="flex-1">
					{#each region.constellations as constellation, constIndex (constellation.id)}
						{@const isLast = constIndex === region.constellations.length - 1}
						{@const firstSystem = constellation.systems[0]}
						<div class="flex">
							<!-- Constellation label (vertical) -->
							<div class="relative mr-1 flex w-14 shrink-0 items-start justify-center pt-1">
								<!-- Vertical line -->
								<div
									class="absolute top-0 left-0 w-px {isLast
										? 'h-4 bg-surface-700'
										: 'h-full bg-surface-700'}"
								></div>
								<!-- Horizontal connector -->
								<div class="absolute top-3 left-0 h-px w-2 bg-surface-700"></div>
								<span
									class="{classColour(firstSystem?.class_name ?? '')} ml-2"
									style="writing-mode: vertical-rl; transform: rotate(180deg); font-size: 11px;"
								>
									{constellation.name}
									<span class="text-surface-500">
										({getDisplayClass(firstSystem?.class_name ?? '?')})
									</span>
								</span>
							</div>

							<!-- Systems list -->
							<div class="relative flex-1 pb-2">
								<!-- Vertical connector for systems -->
								<div
									class="absolute top-0 left-0 w-px bg-surface-700"
									style="height: calc(100% - {constellation.systems.length === 1
										? '12px'
										: '8px'});"
								></div>

								{#each constellation.systems as system (system.id)}
									<div class="flex items-center py-px hover:bg-surface-800/30">
										<!-- Horizontal connector -->
										<div class="h-px w-3 bg-surface-700"></div>

										<!-- System name -->
										<span class="{classColour(system.class_name)} min-w-36 pl-1">
											{system.name}
										</span>

										<!-- Statics with colored targets -->
										<span class="min-w-40">
											{#if system.statics.length > 0}
												{@render staticDisplay(system.statics)}
											{/if}
										</span>

										<!-- Effect -->
										{#if system.effect_name}
											<span class="{effectColour(system.effect_name)} ml-2">
												{system.effect_name}
											</span>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/each}
</div>
