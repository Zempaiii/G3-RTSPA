document.getElementById("submitbutton").addEventListener("click", function(event) {
    event.preventDefault(); 

    const code = document.getElementById("code")?.value;
    const formData = new FormData();
    formData.append('code', code);

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