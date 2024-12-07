document.addEventListener('DOMContentLoaded', function() {
    const emailInput = document.getElementById('email-input');
    const verificationSection = document.getElementById('verification-section');
    const emailSection = document.getElementById('email-section');
    const submitBtn = document.getElementById('submit-btn');
    const verificationCodeInput = document.getElementById('verification-code');
  
    // Handle the submit button click
    submitBtn.addEventListener('click', function(event) {
      event.preventDefault(); // Prevent the form from submitting
  
      // If the current step is the email submission
      if (emailSection.style.display !== 'none') {
        const email = emailInput.value;
        
        // Perform email validation (optional)
        if (!validateEmail(email)) {
          alert('Please enter a valid email address.');
          return;
        }
        
        // Simulate sending verification code (pwede mareplace ng actual API call)
        sendVerificationCode(email);
        
        // Show the verification code input section and hide the email input section
        emailSection.style.display = 'none';
        verificationSection.style.display = 'block';
        submitBtn.value = 'Submit'; 
      } 
      // If the current step is entering the verification code
      else if (verificationSection.style.display !== 'none') {
        const verificationCode = verificationCodeInput.value;
        
        // Perform verification (replace with actual validation logic)
        if (verifyCode(verificationCode)) {
          alert('Verification successful!');
          window.location.href = "login.html"; 
        } else {
          alert('Invalid verification code.');
        }
      }
    });
  
    // Simulated function to validate email format
    function validateEmail(email) {
      const re = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
      return re.test(email);
    }
  
    // Simulated function to send the verification code (replace with real implementation)
    function sendVerificationCode(email) {
      console.log('Sending verification code to: ' + email);
      setTimeout(() => {
        alert('Verification code sent to your email!');
      }, 1000);
    }
  
    // Simulated function to verify the entered verification code (replace with actual logic)
    function verifyCode(code) {
      // Dummy code for testing
      return code === '1234'; 
    }
  });
  