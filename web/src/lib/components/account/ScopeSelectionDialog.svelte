<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import { Dialog, Portal, Switch, Tooltip } from '@skeletonlabs/skeleton-svelte';
	import { CircleHelp } from 'lucide-svelte';
	import { SCOPE_GROUPS, BASIC_SCOPES_DETAILS, buildAuthUrl } from '$lib/helpers/scopeGroups';

	interface Props {
		dialog: ReturnType<typeof import('@skeletonlabs/skeleton-svelte').useDialog>;
		authPath: string;
		title?: string;
		description?: string;
		initialScopes?: string[];
	}

	let {
		dialog,
		authPath,
		title = 'Select Permissions',
		description = 'Choose which permissions to grant:',
		initialScopes = []
	}: Props = $props();

	// Track selected scopes using SvelteSet for reactivity
	let selectedScopes = new SvelteSet<string>();

	// Sync selection when initialScopes prop changes
	$effect(() => {
		selectedScopes.clear();
		for (const scope of initialScopes) {
			selectedScopes.add(scope);
		}
	});

	function toggleScope(scopeId: string) {
		if (selectedScopes.has(scopeId)) {
			selectedScopes.delete(scopeId);
		} else {
			selectedScopes.add(scopeId);
		}
	}

	function handleContinue() {
		const url = buildAuthUrl(authPath, Array.from(selectedScopes));
		window.location.href = url;
	}
</script>

<Dialog.Provider value={dialog}>
	<Portal>
		<Dialog.Backdrop class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
		<Dialog.Positioner class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<Dialog.Content class="w-full max-w-md rounded-lg bg-black/50 p-6 shadow-xl backdrop-blur-sm">
				<Dialog.Title class="mb-2 text-xl font-bold text-white">{title}</Dialog.Title>
				<Dialog.Description class="mb-4 text-sm text-surface-400">
					{description}
				</Dialog.Description>

				<!-- Basic scopes info -->
				<div class="mb-3 rounded-lg border-2 border-surface-800 bg-black/40 p-3">
					<div class="flex items-center gap-2">
						<span class="font-medium text-white">Basic Permissions</span>
						<Tooltip positioning={{ placement: 'right' }}>
							<Tooltip.Trigger>
								<span class="cursor-help text-surface-400 hover:text-surface-300">
									<CircleHelp size={16} />
								</span>
							</Tooltip.Trigger>
							<Portal>
								<Tooltip.Positioner>
									<Tooltip.Content
										class="z-[100] max-w-xs rounded-lg border border-surface-600 bg-surface-800 p-2 text-xs shadow-xl"
									>
										<Tooltip.Arrow
											class="[--arrow-background:var(--color-surface-800)] [--arrow-size:--spacing(2)]"
										>
											<Tooltip.ArrowTip />
										</Tooltip.Arrow>
										<span class="whitespace-pre-line text-white">{BASIC_SCOPES_DETAILS}</span>
									</Tooltip.Content>
								</Tooltip.Positioner>
							</Portal>
						</Tooltip>
					</div>
					<div class="text-sm text-surface-400">Always required for authentication</div>
				</div>

				<div class="space-y-3">
					{#each SCOPE_GROUPS as scope (scope.id)}
						<div
							class="flex items-center justify-between gap-3 rounded-lg border-2 border-surface-800 bg-black/40 p-3"
						>
							<div class="flex-1">
								<div class="flex items-center gap-2">
									<span class="font-medium text-white">{scope.name}</span>
									<Tooltip positioning={{ placement: 'right' }}>
										<Tooltip.Trigger>
											<span class="cursor-help text-surface-400 hover:text-surface-300">
												<CircleHelp size={16} />
											</span>
										</Tooltip.Trigger>
										<Portal>
											<Tooltip.Positioner>
												<Tooltip.Content
													class="z-[100] max-w-xs rounded-lg border border-surface-600 bg-surface-800 p-2 text-xs shadow-xl"
												>
													<Tooltip.Arrow
														class="[--arrow-background:var(--color-surface-800)] [--arrow-size:--spacing(2)]"
													>
														<Tooltip.ArrowTip />
													</Tooltip.Arrow>
													<span class="whitespace-pre-line text-white">{scope.details}</span>
												</Tooltip.Content>
											</Tooltip.Positioner>
										</Portal>
									</Tooltip>
								</div>
								<div class="text-sm text-surface-400">{scope.description}</div>
							</div>
							<Switch
								name={`scope-${scope.id}`}
								checked={selectedScopes.has(scope.id)}
								onCheckedChange={() => toggleScope(scope.id)}
							>
								<Switch.Control>
									<Switch.Thumb />
								</Switch.Control>
								<Switch.HiddenInput />
							</Switch>
						</div>
					{/each}
				</div>

				<div class="mt-6 flex items-center justify-between">
					<Dialog.CloseTrigger class="btn preset-outlined-surface-500">Cancel</Dialog.CloseTrigger>
					<button onclick={handleContinue} class="cursor-pointer border-0 bg-transparent p-0">
						<img src="/eve-login-dark-sm.png" alt="Login with EVE Online" class="h-8" />
					</button>
				</div>
			</Dialog.Content>
		</Dialog.Positioner>
	</Portal>
</Dialog.Provider>
