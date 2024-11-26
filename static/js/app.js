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
  if (results.length > 0 && !results.error) {
    results.forEach(stock => {
      const div = document.createElement("div");
      div.className = "suggestion";

      div.innerHTML = `<a><strong style="margin-left : 20px">${stock.symbol}</strong> - ${stock.name} (${stock.region})</a>`;
      div.onclick = () => {
        search_bar.value = `${stock.symbol} - ${stock.name}`;
        suggestions.innerHTML = ""; 
      };

      suggestions.appendChild(div);
    });
  } else {
    suggestions.innerHTML = `<div id="no-results">No results found</div>`;
  }
});