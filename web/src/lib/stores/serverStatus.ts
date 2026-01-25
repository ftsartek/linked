import { writable } from 'svelte/store';
import type { components } from '$lib/client/schema';

export type EVEStatusResponse = components['schemas']['EVEStatusResponse'];

export const serverStatus = writable<EVEStatusResponse | null>(null);
