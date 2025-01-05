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