// Re-export types from FloatingEdge (they're already defined there)
export type { EdgeType, LifetimeStatus } from '$lib/components/map/FloatingEdge.svelte';

// Re-export API types for convenience
import type { components } from '$lib/client/schema';
import type { EdgeType } from '$lib/components/map/FloatingEdge.svelte';

export type MapInfo = components['schemas']['MapInfo'];
export type CharacterAccessInfo = components['schemas']['CharacterAccessInfo'];
export type CorporationAccessInfo = components['schemas']['CorporationAccessInfo'];
export type AllianceAccessInfo = components['schemas']['AllianceAccessInfo'];

// Map-specific types
export type Rankdir = components['schemas']['RankDir'];

export interface MapSettingsForm {
	name: string;
	description: string;
	is_public: boolean;
	edge_type: EdgeType;
	rankdir: Rankdir;
	auto_layout: boolean;
	node_sep: number;
	rank_sep: number;
	location_tracking_enabled: boolean;
}

export interface ShareableEntity {
	id: number;
	name: string;
	category: 'character' | 'corporation' | 'alliance';
}

export interface NodeCharacterLocation {
	character_name: string;
	corporation_name: string | null;
	alliance_name: string | null;
	ship_type_name: string | null;
	online: boolean | null;
	docked: boolean;
	last_updated: string | null;
}
