// GoatBot TempMail Command
// This module allows users to generate and check temporary emails using the TempMail API

const axios = require('axios');

// Configuration
const config = {
  // Base URL for TempMail API - Update this with your actual deployment URL
  apiBaseUrl: process.env.TEMPMAIL_API_URL || 'http://localhost:5000/api',
  // Cache to store current emails for users
  userEmails: new Map(),
  // Cleanup interval (24 hours in milliseconds)
  cleanupInterval: 24 * 60 * 60 * 1000
};

// Start cleanup process
setInterval(() => {
  const now = Date.now();
  for (const [userId, userData] of config.userEmails.entries()) {
    if (now - userData.timestamp > config.cleanupInterval) {
      config.userEmails.delete(userId);
    }
  }
}, 60 * 60 * 1000); // Run cleanup every hour

module.exports = {
  config: {
    name: "tempmail",
    description: "Generate and manage temporary email addresses",
    usage: "{prefix}tempmail [generate/check/view/delete]",
    aliases: ["tmail", "disposable"],
    cooldown: 10,
    category: "utility"
  },

  onStart: async function({ api, event, args, message }) {
    const userId = event.senderID;
    const subCommand = args[0]?.toLowerCase();

    try {
      switch (subCommand) {
        case "generate":
          await generateEmail(api, event, userId);
          break;
        case "check":
          await checkEmails(api, event, userId);
          break;
        case "view":
          const messageId = args[1];
          if (!messageId) {
            return message.reply("❌ Please provide a message ID to view. Use 'tempmail check' to see all emails first.");
          }
          await viewEmail(api, event, userId, messageId);
          break;
        case "delete":
          const deleteId = args[1];
          if (!deleteId) {
            return message.reply("❌ Please provide a message ID to delete, or use 'all' to delete your temporary email.");
          }
          await deleteEmail(api, event, userId, deleteId);
          break;
        default:
          showHelp(api, event);
      }
    } catch (error) {
      console.error("TempMail command error:", error);
      message.reply("❌ An error occurred while processing your request. Please try again later.");
    }
  }
};

// Generate a new temporary email
async function generateEmail(api, event, userId) {
  try {
    const response = await axios.post(`${config.apiBaseUrl}/generate`);
    
    if (response.status === 201) {
      const email = response.data.email;
      
      // Save email for this user
      config.userEmails.set(userId, {
        email: email,
        timestamp: Date.now()
      });
      
      await api.sendMessage(`✅ Your temporary email has been generated:\n\n📧 ${email}\n\nThis email will expire in 24 hours. Use 'tempmail check' to check for new emails.`, event.threadID);
    } else {
      throw new Error("Failed to generate email");
    }
  } catch (error) {
    console.error("Generate email error:", error);
    await api.sendMessage("❌ Failed to generate a temporary email. Please try again later.", event.threadID);
  }
}

// Check for emails in the temporary mailbox
async function checkEmails(api, event, userId) {
  const userData = config.userEmails.get(userId);
  
  if (!userData || !userData.email) {
    return api.sendMessage("❌ You don't have an active temporary email. Use 'tempmail generate' to create one.", event.threadID);
  }
  
  try {
    const response = await axios.get(`${config.apiBaseUrl}/emails/${userData.email}`);
    
    if (response.status === 200) {
      const messages = response.data.messages;
      
      if (!messages || messages.length === 0) {
        return api.sendMessage(`📭 No emails received yet for ${userData.email}\n\nCheck again later.`, event.threadID);
      }
      
      let messageList = `📬 Emails for ${userData.email}:\n\n`;
      messages.forEach((message, index) => {
        const date = new Date(message.createdAt).toLocaleString();
        const status = message.isRead ? "📖 Read" : "🔵 New";
        messageList += `${index + 1}. ID: ${message.id}\n   From: ${message.from}\n   Subject: ${message.subject || '(No subject)'}\n   ${status} - ${date}\n\n`;
      });
      
      messageList += "To view an email, use 'tempmail view [MESSAGE_ID]'";
      
      await api.sendMessage(messageList, event.threadID);
    } else {
      throw new Error("Failed to fetch emails");
    }
  } catch (error) {
    console.error("Check emails error:", error);
    await api.sendMessage("❌ Failed to check for emails. Please try again later.", event.threadID);
  }
}

// View a specific email
async function viewEmail(api, event, userId, messageId) {
  const userData = config.userEmails.get(userId);
  
  if (!userData || !userData.email) {
    return api.sendMessage("❌ You don't have an active temporary email. Use 'tempmail generate' to create one.", event.threadID);
  }
  
  try {
    const response = await axios.get(`${config.apiBaseUrl}/emails/${userData.email}/${messageId}`);
    
    if (response.status === 200) {
      const email = response.data;
      const date = new Date(email.createdAt).toLocaleString();
      
      let emailContent = `📧 Email Details:\n\n`;
      emailContent += `From: ${email.from}\n`;
      emailContent += `To: ${email.to}\n`;
      emailContent += `Subject: ${email.subject || '(No subject)'}\n`;
      emailContent += `Date: ${date}\n\n`;
      emailContent += `📝 Content:\n\n${email.text || 'No text content available'}\n\n`;
      
      if (email.attachments && email.attachments.length > 0) {
        emailContent += `📎 Has ${email.attachments.length} attachment(s).\n`;
      }
      
      await api.sendMessage(emailContent, event.threadID);
    } else {
      throw new Error("Failed to fetch email content");
    }
  } catch (error) {
    console.error("View email error:", error);
    await api.sendMessage("❌ Failed to retrieve email content. The email may have been deleted or doesn't exist.", event.threadID);
  }
}

// Delete an email or the entire account
async function deleteEmail(api, event, userId, messageId) {
  const userData = config.userEmails.get(userId);
  
  if (!userData || !userData.email) {
    return api.sendMessage("❌ You don't have an active temporary email. Use 'tempmail generate' to create one.", event.threadID);
  }
  
  try {
    if (messageId.toLowerCase() === 'all') {
      // Delete the entire account
      const response = await axios.delete(`${config.apiBaseUrl}/delete/${userData.email}`);
      
      if (response.status === 200) {
        // Remove from our cache
        config.userEmails.delete(userId);
        await api.sendMessage("✅ Your temporary email account has been deleted successfully.", event.threadID);
      } else {
        throw new Error("Failed to delete account");
      }
    } else {
      // Delete a specific email
      const response = await axios.delete(`${config.apiBaseUrl}/emails/${userData.email}/${messageId}`);
      
      if (response.status === 200) {
        await api.sendMessage("✅ Email deleted successfully.", event.threadID);
      } else {
        throw new Error("Failed to delete email");
      }
    }
  } catch (error) {
    console.error("Delete email/account error:", error);
    await api.sendMessage("❌ Failed to delete. The email or account may not exist.", event.threadID);
  }
}

// Show help information
function showHelp(api, event) {
  const helpMessage = `
📧 TempMail Command Usage:

• tempmail generate - Create a new temporary email address
• tempmail check - Check for received emails
• tempmail view [MESSAGE_ID] - View a specific email's content
• tempmail delete [MESSAGE_ID] - Delete a specific email
• tempmail delete all - Delete your temporary email account

Your temporary email will expire after 24 hours.
  `;
  
  api.sendMessage(helpMessage, event.threadID);
}