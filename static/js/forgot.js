document.getElementById("submit-btn").addEventListener("click", function(event) {
  event.preventDefault(); 

  const email = document.getElementById("email-input")?.value;
  const newPassword = document.getElementById("new_password")?.value;
  const formData = new FormData();
  formData.append('email', email);
  formData.append('new_password', newPassword);

  fetch('/forgot', {
      method: 'POST',
      body: formData
  })
  .then(response => response.json())
  .then(data => {
      if (data.success) {
          alert("Verification code sent to your email. Redirecting to verification page.");
          window.location.href = "/verify";
      } else {
          alert("Error: " + data.message);
      }
  })
  .catch(error => {
      console.error('Error:', error);
      alert("An error occurred. Please try again.");
  });
});