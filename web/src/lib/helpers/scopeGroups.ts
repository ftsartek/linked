import { getApiUrl } from '$lib/client/client';

/**
 * Scope group metadata for UI rendering.
 */
export interface ScopeGroupInfo {
	id: string;
	name: string;
	description: string;
	/** Detailed explanation shown in tooltip */
	details: string;
}

/**
 * Basic scopes that are always requested for authentication.
 * These provide fundamental character information.
 */
export const BASIC_SCOPES_DETAILS = `- publicData: allows us to refresh and ensure your character is still yours.`;

/**
 * Available ESI scope groups.
 * Add new entries here as more scope groups are supported by the API.
 */
export const SCOPE_GROUPS: ScopeGroupInfo[] = [
	{
		id: 'location',
		name: 'Location',
		description: 'Allows tracking character location, online status, and current ship',
		details: `- esi-location.read_location.v1: allows us to track your character's location, including what structure/station they're in.
- esi-location.read_online.v1: allows us to check whether your character is online.
- esi-location.read_ship_type.v1: allows us to check what ship and ship type your character is in.
- esi-universe.read_structures.v1: allows us to capture the name of a structure your character is docked in.`
	},
	{
		id: 'search',
		name: 'Search',
		description: 'Allows searching for characters, corporations, and alliances',
		details: `- esi-search.search_structures.v1: the name is a misnomer - allows us to search for structures, characters, corporations, and alliances.`
	}
];

/**
 * Get scope group info by ID.
 */
export function getScopeGroupInfo(id: string): ScopeGroupInfo | undefined {
	return SCOPE_GROUPS.find((g) => g.id === id);
}

/**
 * Build an auth URL with scope query parameters.
 * @param path - API path like '/auth/login' or '/users/characters/link'
 * @param scopes - Array of scope group IDs to include
 * @returns Full URL with scopes as query parameters
 */
export function buildAuthUrl(path: string, scopes: string[]): string {
	const baseUrl = getApiUrl(path);
	if (scopes.length === 0) {
		return baseUrl;
	}
	const params = new URLSearchParams();
	for (const scope of scopes) {
		params.append('scopes', scope);
	}
	return `${baseUrl}?${params.toString()}`;
}
