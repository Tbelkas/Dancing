namespace DancePlatform.API.DTOs.Auth;

/// A provider the server has credentials for — the login page renders one button per entry.
public record ExternalProviderDto(string Name, string DisplayName);

/// What the signup step shows the user before their account exists.
public record SignupTicketDto(string Provider, string? Email, string? Name, string SuggestedUsername);

public class CompleteExternalSignupRequest
{
    public string Ticket { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
}

/// A linked provider on the profile page.
public record LinkedAccountDto(string Provider, string DisplayName, string? Email, DateTime LinkedAt);

/// Whether the account can afford to lose a login method — the UI hides the last "Unlink"
/// button rather than letting the user lock themselves out and then explaining why it failed.
public record LinkedAccountsDto(IReadOnlyList<LinkedAccountDto> Accounts, bool HasPassword);
