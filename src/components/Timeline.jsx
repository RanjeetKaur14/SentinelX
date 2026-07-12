import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip
} from 'chart.js'
import { useTheme } from '../context/ThemeContext'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

const THEME = {
  light: {
    line: '#12897D',
    fillFrom: 'rgba(18,137,125,0.18)',
    fillTo: 'rgba(18,137,125,0)',
    tooltipBg: '#FFFFFF',
    text: '#182322',
    border: '#DEE3E3',
    tick: '#68767A',
    grid: '#EEF1F1'
  },
  dark: {
    line: '#3ADBC4',
    fillFrom: 'rgba(58,219,196,0.25)',
    fillTo: 'rgba(58,219,196,0)',
    tooltipBg: '#12181A',
    text: '#E7EDEE',
    border: '#1F2A2D',
    tick: '#7C8B8E',
    grid: '#1F2A2D'
  }
}

export default function Timeline({ labels, data }) {
  const { isDark } = useTheme()
  const t = isDark ? THEME.dark : THEME.light

  const chartData = {
    labels,
    datasets: [
      {
        data,
        borderColor: t.line,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.35,
        fill: true,
        backgroundColor: (ctx) => {
          const { chart } = ctx
          const { ctx: c, chartArea } = chart
          if (!chartArea) return 'transparent'
          const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          g.addColorStop(0, t.fillFrom)
          g.addColorStop(1, t.fillTo)
          return g
        }
      }
    ]
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: t.tooltipBg,
        titleColor: t.text,
        bodyColor: t.text,
        borderColor: t.border,
        borderWidth: 1,
        titleFont: { family: 'JetBrains Mono', size: 11 },
        bodyFont: { family: 'JetBrains Mono', size: 11 }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: t.tick, font: { family: 'JetBrains Mono', size: 10 }, maxTicksLimit: 6 }
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: t.grid },
        ticks: { color: t.tick, font: { family: 'JetBrains Mono', size: 10 }, maxTicksLimit: 5 }
      }
    }
  }

  return (
    <div className="panel p-5">
      <p className="eyebrow">Risk Score — Last 20 Minutes</p>
      <div className="mt-4 h-40">
        <Line data={chartData} options={options} />
      </div>
    </div>
  )
}
