export function classColour(class_name: string): string {
	switch (class_name) {
		case 'C1':
			return 'text-cyan-400';
		case 'C2':
			return 'text-teal-400';
		case 'C3':
			return 'text-yellow-400';
		case 'C4':
			return 'text-amber-400';
		case 'C5':
			return 'text-orange-400';
		case 'C6':
			return 'text-red-400';
		case 'C13':
			return 'text-slate-400';
		case 'Thera':
			return 'text-slate-400';
		case 'Pochven':
			return 'text-orange-600';
		case 'Sentinel':
			return 'text-rose-400';
		case 'Barbican':
			return 'text-rose-400';
		case 'Vidette':
			return 'text-rose-400';
		case 'Redoubt':
			return 'text-rose-400';
		case 'Conflux':
			return 'text-rose-400';
		case 'HS':
			return 'text-lime-500';
		case 'LS':
			return 'text-yellow-600';
		case 'NS':
			return 'text-red-600';
		default:
			return 'gray';
	}
}

export function shouldShowSecStatus(class_name: string): boolean {
	return class_name === 'HS' || class_name === 'LS' || class_name === 'NS';
}

export function secStatusColour(secStatus?: number | null): string {
	if (!secStatus) {
		return 'text-slate-400';
	}
	if (secStatus >= 0.95) {
		return 'text-blue-600/80';
	} else if (secStatus >= 0.85) {
		return 'text-cyan-500/80';
	} else if (secStatus >= 0.75) {
		return 'text-emerald-500/80';
	} else if (secStatus >= 0.65) {
		return 'text-green-500/80';
	} else if (secStatus >= 0.55) {
		return 'text-lime-500/80';
	} else if (secStatus >= 0.45) {
		return 'text-yellow-400/80';
	} else if (secStatus >= 0.25) {
		return 'text-amber-600/80';
	} else if (secStatus >= 0.0) {
		return 'text-orange-600/80';
	} else {
		return 'text-red-700/80';
	}
}

export function renderSecStatus(secStatus: number): string {
	return secStatus.toFixed(1);
}
