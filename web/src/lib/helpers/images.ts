import { getApiUrl } from '$lib/client/client';

export type EntityType = 'character' | 'corporation' | 'alliance';

/**
 * Get the URL for an EVE entity image via the caching proxy.
 */
export function getEntityImageUrl(
	entityType: EntityType,
	entityId: number,
	size: number = 64
): string {
	return getApiUrl(`/universe/images/${entityType}/${entityId}?size=${size}`);
}

/**
 * Get character portrait URL.
 */
export function getCharacterPortrait(characterId: number, size: number = 64): string {
	return getEntityImageUrl('character', characterId, size);
}

/**
 * Get corporation logo URL.
 */
export function getCorporationLogo(corporationId: number, size: number = 64): string {
	return getEntityImageUrl('corporation', corporationId, size);
}

/**
 * Get alliance logo URL.
 */
export function getAllianceLogo(allianceId: number, size: number = 64): string {
	return getEntityImageUrl('alliance', allianceId, size);
}
