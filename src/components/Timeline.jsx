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

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

export default function Timeline({ labels, data }) {
  const chartData = {
    labels,
    datasets: [
      {
        data,
        borderColor: '#3ADBC4',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.35,
        fill: true,
        backgroundColor: (ctx) => {
          const { chart } = ctx
          const { ctx: c, chartArea } = chart
          if (!chartArea) return 'transparent'
          const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
          g.addColorStop(0, 'rgba(58,219,196,0.25)')
          g.addColorStop(1, 'rgba(58,219,196,0)')
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
        backgroundColor: '#12181A',
        borderColor: '#1F2A2D',
        borderWidth: 1,
        titleFont: { family: 'JetBrains Mono', size: 11 },
        bodyFont: { family: 'JetBrains Mono', size: 11 }
      }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#7C8B8E', font: { family: 'JetBrains Mono', size: 10 }, maxTicksLimit: 6 }
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: '#1F2A2D' },
        ticks: { color: '#7C8B8E', font: { family: 'JetBrains Mono', size: 10 }, maxTicksLimit: 5 }
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
