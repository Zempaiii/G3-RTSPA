const search_bar = document.getElementById('search');
const suggestions = document.getElementById('suggestions');

search_bar.addEventListener("input", async () => {
  const query = search_bar.value.trim();

  if (query.length <= 1) {
    suggestions.innerHTML = "";
    return;
  }
  
  const response = await fetch(`/search?query=${query}`);
  const results = await response.json();

  suggestions.innerHTML = ""; 
  if (response.status === 500) {
    suggestions.innerHTML = `<div id="error">An error occurred while searching. Please try again later.</div>`;
    return;
  }

  if (results.length > 0 && !results.error) {
    results.forEach(stock => {
      const div = document.createElement("div");
      div.className = "suggestion";
      div.innerHTML = `<a class="stocks" href="#" style="color:black; text-decoration:none; margin-left:15px;"><strong>${stock.Symbol}</strong> - ${stock.Name}</a><hr style="margin: 5px;">`;
      div.onclick = async (event) => { 
        event.preventDefault();
        search_bar.value = `${stock.Symbol}`;
        suggestions.innerHTML = "";
        await fetch(`/set_stock?symbol=${stock.Symbol}&name=${stock.Name}`);
        window.location.href = "/spiaa";
      };
      suggestions.appendChild(div);
    });
  } else {
    suggestions.innerHTML = `<div id="no-results">No results found</div>`;
  }
});

document.getElementById('bbtoggleArrowsButton').addEventListener('click', () => {
  const chartData = JSON.parse('{{ chart_data | safe }}');
  const upperBand = chartData.upper_band;
  const lowerBand = chartData.lower_band;
  const middleBand = chartData.middle_band;

  const arrowAnnotations = [
    {
      x: chartData.dates[chartData.dates.length - 1],
      y: upperBand,
      xref: 'x',
      yref: 'y',
      text: 'Upper Band',
      showarrow: true,
      arrowhead: 2,
      ax: 0,
      ay: -40
    },
    {
      x: chartData.dates[chartData.dates.length - 1],
      y: middleBand,
      xref: 'x',
      yref: 'y',
      text: 'Middle Band',
      showarrow: true,
      arrowhead: 2,
      ax: 0,
      ay: -40
    },
    {
      x: chartData.dates[chartData.dates.length - 1],
      y: lowerBand,
      xref: 'x',
      yref: 'y',
      text: 'Lower Band',
      showarrow: true,
      arrowhead: 2,
      ax: 0,
      ay: -40
    }
  ];

  Plotly.relayout('candleChart', {
    annotations: arrowAnnotations
  });
});

document.getElementById('vaToggleArrowsButton').addEventListener('click', () => {
  const chartData = JSON.parse('{{ chart_data | safe }}');
  const pvi = chartData.pvi;
  const nvi = chartData.nvi;

  const arrowAnnotations = [
    {
      x: chartData.dates[chartData.dates.length - 1],
      y: pvi,
      xref: 'x',
      yref: 'y',
      text: 'Positive Volume Index',
      showarrow: true,
      arrowhead: 2,
      ax: 0,
      ay: -40
    },
    {
      x: chartData.dates[chartData.dates.length - 1],
      y: nvi,
      xref: 'x',
      yref: 'y',
      text: 'Negative Volume Index',
      showarrow: true,
      arrowhead: 2,
      ax: 0,
      ay: -40
    }
  ];

  Plotly.relayout('candleChart', {
    annotations: arrowAnnotations
  });
});

document.getElementById('srToggleArrowsButton').addEventListener('click', () => {
  const chartData = JSON.parse('{{ chart_data | safe }}');
  const support = chartData.support;
  const resistance = chartData.resistance;

  const arrowAnnotations = [
    {
      x: chartData.dates[chartData.dates.length - 1],
      y: support,
      xref: 'x',
      yref: 'y',
      text: 'Support',
      showarrow: true,
      arrowhead: 2,
      ax: 0,
      ay: -40
    },
    {
      x: chartData.dates[chartData.dates.length - 1],
      y: resistance,
      xref: 'x',
      yref: 'y',
      text: 'Resistance',
      showarrow: true,
      arrowhead: 2,
      ax: 0,
      ay: -40
    }
  ];

  Plotly.relayout('candleChart', {
    annotations: arrowAnnotations
  });
});