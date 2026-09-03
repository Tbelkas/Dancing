using System.Net;
using System.Net.Mail;

namespace DancePlatform.API.Services;

public interface IEmailSender
{
    /// <summary>False when no SMTP server is configured — the caller decides whether that is
    /// fatal. It never is: a reset request must answer identically either way.</summary>
    bool IsConfigured { get; }

    Task<bool> SendAsync(string to, string subject, string body, CancellationToken ct = default);
}

/// <summary>
/// Plain SMTP, configured the same way social sign-in is: absent credentials mean the feature
/// is dormant rather than broken, so the API boots and runs on a dev box with no secrets.
/// When it is dormant the message is written to the log at Warning instead of being sent,
/// which is what makes the reset flow testable locally — the link is in the journal.
/// </summary>
public class SmtpEmailSender : IEmailSender
{
    private readonly IConfiguration _config;
    private readonly ILogger<SmtpEmailSender> _log;

    public SmtpEmailSender(IConfiguration config, ILogger<SmtpEmailSender> log)
    {
        _config = config;
        _log = log;
    }

    public bool IsConfigured => !string.IsNullOrWhiteSpace(_config["Email:Smtp:Host"])
                             && !string.IsNullOrWhiteSpace(_config["Email:From"]);

    public async Task<bool> SendAsync(string to, string subject, string body, CancellationToken ct = default)
    {
        if (!IsConfigured)
        {
            _log.LogWarning(
                "No SMTP configured; not sending mail to {Recipient}. Subject: {Subject}\n{Body}",
                to, subject, body);
            return false;
        }

        using var message = new MailMessage
        {
            From = new MailAddress(_config["Email:From"]!, _config["Email:FromName"] ?? "Dance Platform"),
            Subject = subject,
            Body = body,
            IsBodyHtml = false
        };
        message.To.Add(to);

        using var client = new SmtpClient(_config["Email:Smtp:Host"], _config.GetValue("Email:Smtp:Port", 587))
        {
            EnableSsl = _config.GetValue("Email:Smtp:UseSsl", true)
        };
        var user = _config["Email:Smtp:User"];
        if (!string.IsNullOrWhiteSpace(user))
            client.Credentials = new NetworkCredential(user, _config["Email:Smtp:Password"]);

        try
        {
            await client.SendMailAsync(message, ct);
            return true;
        }
        catch (Exception ex) when (ex is SmtpException or InvalidOperationException)
        {
            // A dead mail server must not turn "I forgot my password" into a 500 that tells
            // the caller something went wrong on a specific address.
            _log.LogError(ex, "Failed to send mail to {Recipient}", to);
            return false;
        }
    }
}
