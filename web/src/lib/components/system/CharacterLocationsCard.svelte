<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { Progress } from '@skeletonlabs/skeleton-svelte';
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { apiClient } from '$lib/client/client';
	import { getCharacterPortrait } from '$lib/helpers/images';
	import type { components } from '$lib/client/schema';

	type CharacterLocationData = components['schemas']['CharacterLocationData'];
	type CharacterLocationError = components['schemas']['CharacterLocationError'];
	type CharacterInfo = components['schemas']['users_service_CharacterInfo'];

	// Refresh intervals
	const ONLINE_REFRESH_INTERVAL = 15 * 1000; // 15 seconds
	const OFFLINE_REFRESH_INTERVAL = 2 * 60 * 1000; // 2 minutes

	let characters = $state<CharacterInfo[]>([]);
	const locationData = new SvelteMap<number, CharacterLocationData>();
	const locationErrors = new SvelteMap<number, CharacterLocationError>();
	const loadingChars = new SvelteSet<number>();
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- timers don't need reactivity
	const charTimers = new Map<number, ReturnType<typeof setTimeout>>();
	let loading = $state(false);
	let error = $state<string | null>(null);

	// Current time that updates every 5 seconds to force re-render of relative timestamps
	let now = $state(Date.now());
	let nowInterval: ReturnType<typeof setInterval> | null = null;

	// Fetch character list on mount
	async function loadCharacters() {
		const { data } = await apiClient.GET('/users/characters');
		if (data?.characters) {
			characters = data.characters;
		}
	}

	// Schedule next refresh for a character based on online status
	function scheduleCharacterRefresh(characterId: number, isOnline: boolean | null) {
		// Clear any existing timer
		const existingTimer = charTimers.get(characterId);
		if (existingTimer) {
			clearTimeout(existingTimer);
		}

		// Schedule next refresh - online chars refresh faster
		const interval = isOnline ? ONLINE_REFRESH_INTERVAL : OFFLINE_REFRESH_INTERVAL;
		const timer = setTimeout(() => {
			refreshCharacter(characterId);
		}, interval);
		charTimers.set(characterId, timer);
	}

	// Refresh a single character's location
	async function refreshCharacter(characterId: number) {
		loadingChars.add(characterId);

		const { data, response } = await apiClient.POST(
			'/users/characters/{character_id}/location/refresh',
			{ params: { path: { character_id: characterId } } }
		);

		loadingChars.delete(characterId);

		if (!data) {
			// Network error or unexpected failure - schedule retry
			scheduleCharacterRefresh(characterId, false);
			return;
		}

		if (response.ok) {
			// Success - we have valid location data
			const charData = data as CharacterLocationData;
			const previousData = locationData.get(characterId);
			const wasOffline = previousData?.online === false;
			const isNowOnline = charData.online === true;

			locationData.set(characterId, charData);
			locationErrors.delete(characterId);

			// If character just came online, refresh again shortly to get fresh location/ship
			if (wasOffline && isNowOnline) {
				setTimeout(() => refreshCharacter(characterId), 1000);
			} else {
				// Schedule next refresh based on online status
				scheduleCharacterRefresh(characterId, charData.online ?? null);
			}
		} else {
			// Error response - store error and determine retry behavior by status code
			const charError = data as CharacterLocationError;
			locationErrors.set(characterId, charError);
			locationData.delete(characterId);

			// 503 (ESI error) and 424 (missing data) are transient - retry
			// 403 (no scope/token issues) are persistent - no retry
			if (response.status === 503 || response.status === 424) {
				scheduleCharacterRefresh(characterId, false);
			}
		}
	}

	// Refresh all characters (initial load or manual refresh)
	async function refreshAllLocations() {
		if (characters.length === 0) {
			await loadCharacters();
		}

		loading = true;
		error = null;

		// Clear all existing timers
		for (const timer of charTimers.values()) {
			clearTimeout(timer);
		}
		charTimers.clear();

		// Refresh all characters concurrently
		await Promise.all(characters.map((char) => refreshCharacter(char.id)));

		loading = false;
	}

	// Get sorted location data as array
	function getLocationDataArray(): CharacterLocationData[] {
		return Array.from(locationData.values()).sort((a, b) =>
			a.character_name.localeCompare(b.character_name)
		);
	}

	// Get sorted error data as array
	function getLocationErrorsArray(): CharacterLocationError[] {
		return Array.from(locationErrors.values()).sort((a, b) =>
			a.character_name.localeCompare(b.character_name)
		);
	}

	// Auto-load on mount and start time update interval
	onMount(() => {
		refreshAllLocations();
		// Update relative timestamps every 5 seconds
		nowInterval = setInterval(() => {
			now = Date.now();
		}, 5000);
	});

	// Cleanup timers on destroy
	onDestroy(() => {
		for (const timer of charTimers.values()) {
			clearTimeout(timer);
		}
		charTimers.clear();
		if (nowInterval) {
			clearInterval(nowInterval);
		}
	});

	function formatLastUpdated(dateStr: string, currentTime: number): string {
		const date = new Date(dateStr);
		const diffMs = currentTime - date.getTime();
		const diffSecs = Math.floor(diffMs / 1000);

		if (diffSecs < 60) return `${diffSecs}s ago`;
		if (diffSecs < 600) {
			const mins = Math.floor(diffSecs / 60);
			const secs = diffSecs % 60;
			return `${mins}m ${secs}s ago`;
		}
		if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
		const hours = Math.floor(diffSecs / 3600);
		const mins = Math.floor((diffSecs % 3600) / 60);
		return `${hours}h ${mins}m ago`;
	}

	function getErrorMessage(errorCode: string): string {
		switch (errorCode) {
			case 'no_scope':
				return 'No location scope';
			case 'token_expired':
				return 'Token expired';
			case 'token_revoked':
				return 'Token revoked';
			case 'esi_error':
				return 'ESI error';
			case 'server_error':
				return 'Server data unavailable';
			default:
				return errorCode;
		}
	}
</script>

<div class="flex h-full min-h-80 flex-col rounded-xl border-0 bg-surface-950/75 backdrop-blur-2xl">
	<!-- Header -->
	<div class="flex w-full flex-col border-b-2 border-secondary-950/50">
		<div class="flex flex-row items-center justify-between px-3 py-2">
			<h3 class="text-sm font-semibold text-white">Character Locations</h3>
		</div>
		{#if loading}
			<Progress value={null} class="h-0.5 w-full">
				<Progress.Track class="h-0.5 rounded-none bg-transparent">
					<Progress.Range class="h-0.5 rounded-none bg-primary-300-700" />
				</Progress.Track>
			</Progress>
		{/if}
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-auto p-2">
		{#if error}
			<div class="flex h-full items-center justify-center">
				<p class="text-sm text-error-500">{error}</p>
			</div>
		{:else if locationData.size === 0 && locationErrors.size === 0 && !loading}
			<div class="flex h-full flex-col items-center justify-center gap-2">
				<p class="text-sm text-surface-400">No characters with location tracking</p>
			</div>
		{:else}
			<div class="flex flex-col gap-2">
				<!-- Characters with location data -->
				{#each getLocationDataArray() as char (char.character_id)}
					<div
						class="flex items-center gap-2 rounded-lg bg-primary-700/15 p-2"
						class:opacity-60={char.is_stale}
					>
						<!-- Portrait -->
						<img
							src={getCharacterPortrait(char.character_id, 64)}
							alt={char.character_name}
							class="size-10 rounded"
						/>

						<!-- Info -->
						<div class="flex min-w-0 flex-1 flex-col">
							<div class="flex items-center gap-2">
								<span class="truncate text-sm font-medium text-white">
									{char.character_name}
								</span>
								{#if char.online === true}
									<span class="size-2 rounded-full bg-success-500" title="Online"></span>
								{:else if char.online === false}
									<span class="size-2 rounded-full bg-surface-600" title="Offline"></span>
								{/if}
							</div>

							<div class="flex items-center gap-1 text-xs text-surface-400">
								{#if char.structure_name}
									<span class="truncate">{char.structure_name}</span>
								{:else if char.station_name}
									<span class="truncate">{char.station_name}</span>
								{:else if char.solar_system_name}
									<span class="truncate">{char.solar_system_name}</span>
								{:else if char.solar_system_id}
									<span>System {char.solar_system_id}</span>
								{:else}
									<span class="text-surface-500">Unknown location</span>
								{/if}
							</div>

							<div class="flex items-center gap-1 text-xs text-surface-400">
								{#if char.ship_type_name}
									<span class="truncate text-surface-500">{char.ship_type_name}</span>
									{#if char.ship_name}
										<span class="truncate">"{char.ship_name}"</span>
									{/if}
								{:else if char.ship_name}
									<span class="truncate">{char.ship_name}</span>
								{/if}
							</div>

							<div class="flex items-center gap-2 text-xs">
								<span class="text-surface-500">
									{formatLastUpdated(char.last_updated, now)}
								</span>
							</div>
						</div>
					</div>
				{/each}

				<!-- Characters with errors -->
				{#each getLocationErrorsArray() as charError (charError.character_id)}
					<div class="flex items-center gap-2 rounded-lg bg-primary-800/20 p-2">
						<!-- Portrait -->
						<img
							src={getCharacterPortrait(charError.character_id, 64)}
							alt={charError.character_name}
							class="size-10 rounded grayscale"
						/>

						<!-- Info -->
						<div class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-sm font-medium text-surface-400">
								{charError.character_name}
							</span>
							<span class="text-xs text-error-400">
								{getErrorMessage(charError.error)}
							</span>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
