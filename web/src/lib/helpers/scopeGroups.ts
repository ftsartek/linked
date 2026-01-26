import { getApiUrl } from '$lib/client/client';

/**
 * Scope group metadata for UI rendering.
 */
export interface ScopeGroupInfo {
	id: string;
	name: string;
	description: string;
}

/**
 * Available ESI scope groups.
 * Add new entries here as more scope groups are supported by the API.
 */
export const SCOPE_GROUPS: ScopeGroupInfo[] = [
	{
		id: 'location',
		name: 'Location',
		description: 'Allows tracking character location, online status, and current ship'
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
