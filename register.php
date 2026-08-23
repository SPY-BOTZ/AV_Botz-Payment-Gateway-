<?php
// Database connection ya configuration file include karein (agar alag file hai toh apna naam yahan daalein)
// include 'db.php'; 

// Agar aapka code session ya connection alag file mein nahi hai, toh yahan direct connection likh sakte hain
// Neeche sample signup logic hai jisme Telegram notification add kiya gaya hai:

if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    
    // Form se aane wale data ko receive karein (Apne form ke input name ke hisaab se check kar lein)
    $name = isset($_POST['name']) ? trim($_POST['name']) : '';
    $email = isset($_POST['email']) ? trim($_POST['email']) : '';
    $mobile = isset($_POST['mobile']) ? trim($_POST['mobile']) : '';
    $password = isset($_POST['password']) ? $_POST['password'] : '';

    // Validation check
    if(empty($name) || empty($email) || empty($mobile) || empty($password)) {
        echo "<script>alert('Please fill all fields!'); window.history.back();</script>";
        exit;
    }

    // --- YAHAN AAP APNI DATABASE INSERT QUERY LAGA RAHE HONGE ---
    // Example: $sql = "INSERT INTO users (name, email, mobile, password) VALUES ('$name', '$email', '$mobile', '$password')";
    // $result = mysqli_query($conn, $sql);

    // Maan lijiye signup successful ho gaya, ab yahan Telegram notification trigger hoga:
    $signup_success = true; // Yeh true tab hoga jab database mein query successfully run ho jaye

    if ($signup_success) {
        
        // --- TELEGRAM CHANNEL CONFIGURATION ---
        $botToken = "8432557033:AAGts8uHMdhRVaNFTHX3_tp2VYUEZQGEr78";       // Yahan apna Telegram Bot Token daalein (@BotFather wala)
        $chatId = "-1002580860502";       // Yahan apne Channel ka username (jaise @mychannel) ya numeric ID daalein (-100xxxxxxx)

        // Jo message channel par bhejna hai uska format
        $message = "🎉 *New Member Signup!* 🎉\n\n" .
                   "👤 *Name:* " . $name . "\n" .
                   "📧 *Email:* " . $email . "\n" .
                   "📱 *Mobile:* " . $mobile . "\n" .
                   "🌐 *Gateway:* FamPay Gateway";

        $website_api = "https://usual-catshark-moveshub-450ea334.koyeb.app/" . $botToken . "/sendMessage";
        $params = [
            'chat_id' => $chatId,
            'text' => $message,
            'parse_mode' => 'Markdown'
        ];

        // cURL ke zariye Telegram par message bhejna
        $ch = curl_init($website_api);
        curl_setopt($ch, CURLOPT_HEADER, false);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_POST, 1);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $params);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        $result = curl_exec($ch);
        curl_close($ch);

        // Success response ya redirection
        echo "<script>alert('Registration Successful!'); window.location.href='login.php';</script>";
        exit;
    } else {
        echo "<script>alert('Registration Failed. Try again!'); window.history.back();</script>";
    }
}
?>
  
