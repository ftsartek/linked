import { writable } from 'svelte/store';
import type { components } from '$lib/client/schema';

export type UserInfo = components['schemas']['UserInfo'];

export const user = writable<UserInfo | null | undefined>(undefined);
