export const RISK_COLORS_LIGHT = {
  green: '#1E9A5C',
  yellow: '#B4860F',
  orange: '#C86A24',
  red: '#C93B3B'
}

export const RISK_COLORS_DARK = {
  green: '#37D67A',
  yellow: '#E8C547',
  orange: '#F2924B',
  red: '#E5484D'
}

export const RISK_LABELS = {
  green: 'Normal',
  yellow: 'Elevated',
  orange: 'Congested',
  red: 'Critical'
}

export function getRiskColors(isDark) {
  return isDark ? RISK_COLORS_DARK : RISK_COLORS_LIGHT
}

export function scoreToLevel(score) {
  if (score >= 80) return 'red'
  if (score >= 55) return 'orange'
  if (score >= 30) return 'yellow'
  return 'green'
}
