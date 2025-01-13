function openPopup(platform) {
    const popup = document.getElementById("popup-modal");
    const accountOptions = document.getElementById("account-options");
  
    // Add mock accounts based on the selected platform
    const accounts =
      platform === "facebook"
        ? ["john.doe@facebook.com", "jane.doe@facebook.com"]
        : ["john.doe@gmail.com", "jane.doe@gmail.com"];
  
    accountOptions.innerHTML = accounts
      .map(
        (account) =>
          `<div class="account-option">
             <input type="radio" id="${account}" name="account" value="${account}">
             <label for="${account}">${account}</label>
           </div>`
      )
      .join("");
  
    // Remove the hidden class to show the modal
    popup.classList.remove("hidden");
  }
  
  function closePopup() {
    // Add the hidden class to hide the modal
    document.getElementById("popup-modal").classList.add("hidden");
  }
  