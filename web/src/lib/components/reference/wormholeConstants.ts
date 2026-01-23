import type { components } from '$lib/client/schema';

export type WormholeSummary = components['schemas']['ListWormholesWormholeTypeSummaryResponseBody'];
export type WormholeDetail = components['schemas']['GetWormholeWormholeTypeDetailResponseBody'];

export function formatMass(mass: number | null | undefined): string {
	if (mass === null || mass === undefined) return '-';
	if (mass >= 1_000_000_000) {
		return `${(mass / 1_000_000_000).toFixed(1)} Billion kg`;
	}
	if (mass >= 1_000_000) {
		return `${(mass / 1_000_000).toFixed(0)} Million kg`;
	}
	return `${mass.toLocaleString()} kg`;
}

export function getShipClassLimit(mass: number | null | undefined): string | null {
	if (mass === null || mass === undefined) return null;
	if (mass <= 5_000_000) return 'up to Destroyer';
	if (mass <= 62_000_000) return 'up to Battlecruiser';
	if (mass <= 375_000_000) return 'up to Battleship';
	if (mass <= 1_000_000_000) return 'up to Capital';
	return null;
}

export function formatLifetime(hours: number | null | undefined): string {
	if (hours === null || hours === undefined) return '-';
	return `${hours} hours`;
}
