import { apiClient } from '$lib/client/client';

export interface ViewportState {
	x: number;
	y: number;
	zoom: number;
}

export async function loadViewport(mapId: string): Promise<ViewportState | null> {
	const { data } = await apiClient.GET('/users/preferences');
	const savedViewport = data?.viewports?.[mapId];

	if (savedViewport) {
		return {
			x: savedViewport.x,
			y: savedViewport.y,
			zoom: savedViewport.zoom
		};
	}
	return null;
}

export async function setSelectedMap(mapId: string): Promise<void> {
	await apiClient.PATCH('/users/preferences', {
		body: { selected_map_id: mapId }
	});
}

export function createViewportPersister(mapId: string) {
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let lastPersisted: ViewportState | null = null;

	const persist = (viewport: ViewportState) => {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}

		debounceTimer = setTimeout(async () => {
			// Skip if viewport hasn't actually changed
			if (
				lastPersisted &&
				Math.abs(viewport.x - lastPersisted.x) < 0.1 &&
				Math.abs(viewport.y - lastPersisted.y) < 0.1 &&
				Math.abs(viewport.zoom - lastPersisted.zoom) < 0.001
			) {
				return;
			}

			await apiClient.PATCH('/users/preferences/maps/{map_id}/viewport', {
				params: { path: { map_id: mapId } },
				body: { viewport }
			});

			lastPersisted = { ...viewport };
		}, 500);
	};

	const cleanup = () => {
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}
	};

	return { persist, cleanup };
}
