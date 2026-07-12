export const RISK_COLORS = {
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

export function scoreToLevel(score) {
  if (score >= 80) return 'red'
  if (score >= 55) return 'orange'
  if (score >= 30) return 'yellow'
  return 'green'
}

export function riskTextClass(level) {
  return {
    green: 'text-risk-green',
    yellow: 'text-risk-yellow',
    orange: 'text-risk-orange',
    red: 'text-risk-red'
  }[level]
}

export function riskBgClass(level) {
  return {
    green: 'bg-risk-green',
    yellow: 'bg-risk-yellow',
    orange: 'bg-risk-orange',
    red: 'bg-risk-red'
  }[level]
}
