document.getElementById("submitbutton").addEventListener("click", function(event) {
  event.preventDefault(); 

  const email = document.getElementById("email")?.value;
  const newPassword = document.getElementById("new_password")?.value;
  const formData = new FormData();
  formData.append('email', email);
  formData.append('new_password', newPassword);

  fetch('/verify', {
      method: 'POST',
      body: formData
  })
  .then(response => response.json())
  .then(data => {
          alert(response)
      if (data.success) {
          alert("Verification successful!");
      } else {
          alert("Verification failed: " + data.message);
      }
  })
  .catch(error => {
      alert(response, data)
      console.error('Error:', error);
      alert("An error occurred during verification. error: " + error);
  });
  
});