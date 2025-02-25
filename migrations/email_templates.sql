-- Keep this for custom notifications (not auth-related)
CREATE TABLE IF NOT EXISTS email_templates (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(255) NOT NULL UNIQUE,
    subject VARCHAR(255) NOT NULL,
    content TEXT NOT NULL
);

-- Welcome email template
INSERT INTO email_templates (name, subject, content) VALUES
('welcome', 'Welcome to PykhBrain Bot!', '
<h2>Welcome to PykhBrain Bot!</h2>
<p>Your account "{{account_name}}" has been successfully created!</p>
<p>You can now:</p>
<ul>
    <li>Access your dashboard at {{dashboard_url}}</li>
    <li>Add the bot to more groups</li>
    <li>Customize your settings</li>
    <li>View conversation history</li>
</ul>
<p>Need help? Just reply to the bot with /help</p>
')
ON CONFLICT (name) DO NOTHING;

-- Function to send custom emails
CREATE OR REPLACE FUNCTION send_notification_email(
    p_email TEXT,
    p_subject TEXT,
    p_content TEXT
) RETURNS VOID AS $$
BEGIN
    -- Use Supabase's email service
    PERFORM auth.send_email(
        p_email,
        p_subject,
        p_content
    );
END;
$$ LANGUAGE plpgsql; 