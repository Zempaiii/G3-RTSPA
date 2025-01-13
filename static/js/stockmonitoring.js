document.addEventListener('DOMContentLoaded', function() {
    const table = document.getElementById('stockTable');
    const noStocksMessage = document.getElementById('noStocksMessage');
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
  
    if (rows.length === 0) {
      noStocksMessage.style.display = 'block';
    } else {
      noStocksMessage.style.display = 'none';
      updateChart();
    }
  
    function sortTable(columnIndex) {
      const tbody = table.getElementsByTagName('tbody')[0];
      const rowsArray = Array.from(tbody.rows);
      const sortedRows = rowsArray.sort((a, b) => {
        const aText = a.cells[columnIndex].innerText;
        const bText = b.cells[columnIndex].innerText;
        return aText.localeCompare(bText);
      });
      tbody.innerHTML = '';
      sortedRows.forEach(row => tbody.appendChild(row));
      updateChart();
    }
  
    function updateChart() {
      const symbols = [];
      const closePrices = [];
      for (let i = 0; i < Math.min(5, rows.length); i++) {
        symbols.push(rows[i].cells[0].innerText);
        closePrices.push(parseFloat(rows[i].cells[2].innerText));
      }
  
      const data = [{
        x: symbols,
        y: closePrices,
        type: 'bar'
      }];
  
      Plotly.newPlot('lineChart', data);
    }
  
    window.sortTable = sortTable;
  });