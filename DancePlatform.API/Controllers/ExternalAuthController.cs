using System.Security.Claims;
using DancePlatform.API.DTOs.Auth;
using DancePlatform.API.Services;
using DancePlatform.API.Services.ExternalAuth;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

/// The provider-agnostic half of social sign-in. Everything provider-specific lives behind
/// IExternalAuthProvider; this controller owns state, PKCE, account resolution and redirects.
[ApiController]
[Route("api/auth/external")]
public class ExternalAuthController : ControllerBase
{
    private readonly IExternalAuthService _external;
    private readonly OAuthStateProtector _state;
    private readonly ITokenService _tokens;
    private readonly IConfiguration _config;
    private readonly ILogger<ExternalAuthController> _log;

    public ExternalAuthController(
        IExternalAuthService external, OAuthStateProtector state, ITokenService tokens,
        IConfiguration config, ILogger<ExternalAuthController> log)
    {
        _external = external;
        _state = state;
        _tokens = tokens;
        _config = config;
        _log = log;
    }

    /// Which buttons the login page should render. A dev box with no secrets returns an empty
    /// list, so the page degrades to the password form instead of offering a dead button.
    [HttpGet("providers")]
    public ActionResult<IReadOnlyList<ExternalProviderDto>> Providers() =>
        Ok(_external.ConfiguredProviders());

    /// Sends the browser to the provider's consent screen. A top-level navigation, so it takes
    /// no bearer token and can only ever start a sign-in — never a link.
    [HttpGet("{provider}/start")]
    public IActionResult Start(string provider)
    {
        var impl = _external.Find(provider);
        if (impl is null) return NotFound();

        return Redirect(BuildAuthorizeUrl(impl, linkUserId: null));
    }

    /// Link mode. A POST from the profile page rather than a navigation, specifically so the
    /// caller's identity arrives in the Authorization header instead of the query string.
    [Authorize]
    [HttpPost("{provider}/link-start")]
    public IActionResult LinkStart(string provider)
    {
        var impl = _external.Find(provider);
        if (impl is null) return NotFound();

        var userId = CurrentUserId();
        if (userId is null) return Unauthorized();

        return Ok(new { url = BuildAuthorizeUrl(impl, userId) });
    }

    [HttpGet("{provider}/callback")]
    public async Task<IActionResult> Callback(
        string provider, [FromQuery] string? code, [FromQuery] string? state,
        [FromQuery] string? error, CancellationToken ct)
    {
        // The user pressed "Cancel" on the consent screen. Not an error worth showing.
        if (!string.IsNullOrEmpty(error))
            return Redirect(UiUrl("/login"));

        var impl = _external.Find(provider);
        if (impl is null) return NotFound();

        var unprotected = _state.Unprotect(state);
        // Forged, expired, or replayed state. This check is what stops an attacker from invoking
        // the callback with a code of their own and logging the victim into the attacker's account.
        if (unprotected is null || unprotected.Provider != impl.Name || string.IsNullOrEmpty(code))
            return Redirect(UiUrl("/login?error=oauth_state"));

        var identity = await impl.ExchangeCodeAsync(
            code, RedirectUriFor(impl), unprotected.CodeVerifier, ct);
        if (identity is null)
            return Redirect(UiUrl("/login?error=oauth_failed"));

        return unprotected.LinkUserId is int linkUserId
            ? await CompleteLinkAsync(impl, identity, linkUserId, ct)
            : await CompleteSignInAsync(impl, identity, ct);
    }

    private async Task<IActionResult> CompleteSignInAsync(
        IExternalAuthProvider impl, ExternalIdentity identity, CancellationToken ct)
    {
        var user = await _external.FindUserAsync(impl.Name, identity.Subject, ct);
        if (user is not null)
        {
            // Fragment, not query string: the token must not land in Apache's access log on the
            // Pi or in a Referer header on the next outbound request.
            var token = _tokens.CreateAccessToken(user);
            return Redirect($"{UiUrl("/auth/callback")}#token={Uri.EscapeDataString(token)}");
        }

        // First time we've seen this provider identity — no account yet. Hand back a ticket the
        // signup screen can spend once the user has chosen a username.
        var ticket = _tokens.CreateSignupTicket(impl.Name, identity);
        return Redirect($"{UiUrl("/finish-signup")}#ticket={Uri.EscapeDataString(ticket)}");
    }

    private async Task<IActionResult> CompleteLinkAsync(
        IExternalAuthProvider impl, ExternalIdentity identity, int userId, CancellationToken ct)
    {
        var result = await _external.LinkAsync(userId, impl.Name, identity, ct);
        var status = result switch
        {
            LinkResult.Linked or LinkResult.AlreadyLinkedToYou => $"linked={impl.Name}",
            _ => $"linkError={impl.Name}"
        };
        return Redirect(UiUrl($"/profile?{status}"));
    }

    /// Describes an unspent ticket so the signup screen can show who signed in and prefill a
    /// username. Deliberately a POST: a ticket in a query string ends up in server logs.
    [HttpPost("ticket")]
    public async Task<ActionResult<SignupTicketDto>> InspectTicket(
        [FromBody] TicketRequest request, CancellationToken ct)
    {
        var parsed = _tokens.ReadSignupTicket(request.Ticket ?? string.Empty);
        if (parsed is null) return Unauthorized(new { message = "This sign-up link has expired. Please sign in again." });

        var (provider, identity) = parsed.Value;
        return Ok(await _external.DescribeTicketAsync(provider, identity, ct));
    }

    [HttpPost("complete")]
    public async Task<IActionResult> Complete(
        [FromBody] CompleteExternalSignupRequest request, CancellationToken ct)
    {
        var parsed = _tokens.ReadSignupTicket(request.Ticket ?? string.Empty);
        if (parsed is null) return Unauthorized(new { message = "This sign-up link has expired. Please sign in again." });

        var username = (request.Username ?? string.Empty).Trim();
        if (username.Length < 3)
            return BadRequest(new { message = "Username must be at least 3 characters." });
        if (!username.All(c => char.IsAsciiLetterOrDigit(c) || c is '_' or '-'))
            return BadRequest(new { message = "Username can only contain letters, numbers, _ and -." });

        var (provider, identity) = parsed.Value;
        var result = await _external.CompleteSignupAsync(provider, identity, username, ct);
        if (result is null)
            return Conflict(new { message = "Username already taken." });

        var created = result.Username;
        _log.LogInformation("Created account {Username} via {Provider}", created, provider);
        return Ok(result);
    }

    [Authorize]
    [HttpGet("links")]
    public async Task<ActionResult<LinkedAccountsDto>> Links(CancellationToken ct)
    {
        var userId = CurrentUserId();
        if (userId is null) return Unauthorized();
        return Ok(await _external.GetLinkedAccountsAsync(userId.Value, ct));
    }

    [Authorize]
    [HttpDelete("links/{provider}")]
    public async Task<IActionResult> Unlink(string provider, CancellationToken ct)
    {
        var userId = CurrentUserId();
        if (userId is null) return Unauthorized();

        return await _external.UnlinkAsync(userId.Value, provider, ct) switch
        {
            UnlinkResult.Unlinked => NoContent(),
            UnlinkResult.NotLinked => NotFound(new { message = "That account isn't linked." }),
            _ => Conflict(new { message = "This is your only way to sign in. Set a password first." })
        };
    }

    /// Meta requires a data-deletion callback before a Facebook app may go Live. It posts a
    /// signed_request naming a user; we unlink that provider identity and report back a URL the
    /// person can visit to see the status.
    ///
    /// Unlinking, not deleting the account: the user may well have a password or a second
    /// provider, and their practice history isn't Facebook's to erase. If Facebook was their only
    /// way in, the account is left without a login — which is the correct reading of the request.
    [HttpPost("facebook/data-deletion")]
    public async Task<IActionResult> FacebookDataDeletion(
        [FromForm(Name = "signed_request")] string? signedRequest, CancellationToken ct)
    {
        if (_external.Find("facebook") is not FacebookAuthProvider facebook)
            return NotFound();

        var subject = facebook.ReadSignedRequestUserId(signedRequest);
        if (subject is null) return BadRequest(new { message = "Invalid signed_request." });

        var user = await _external.FindUserAsync("facebook", subject, ct);
        if (user is not null)
        {
            var userId = user.Id;
            await _external.ForceUnlinkAsync(userId, "facebook", ct);
            _log.LogInformation("Honoured Facebook data-deletion request for user {UserId}", userId);
        }

        // Meta expects this exact shape: a status URL and a code it can quote back to the user.
        var code = Guid.NewGuid().ToString("N")[..12];
        return Ok(new
        {
            url = UiUrl($"/data-deletion?code={code}"),
            confirmation_code = code
        });
    }

    private string BuildAuthorizeUrl(IExternalAuthProvider impl, int? linkUserId)
    {
        var verifier = OAuthStateProtector.NewCodeVerifier();
        var state = _state.Protect(new OAuthState(
            impl.Name,
            verifier,
            Guid.NewGuid().ToString("N"),
            DateTimeOffset.UtcNow.Add(OAuthStateProtector.Lifetime).ToUnixTimeSeconds(),
            linkUserId));

        return impl.BuildAuthorizeUrl(
            RedirectUriFor(impl), state, OAuthStateProtector.CodeChallengeFor(verifier));
    }

    /// Must match the URI registered with the provider byte for byte, which is why it is built
    /// from configuration rather than from the incoming request (Apache proxies to Kestrel over
    /// plain HTTP, so Request.Scheme here is "http", not the "https" the provider was given).
    private string RedirectUriFor(IExternalAuthProvider impl) =>
        $"{_config["App:ApiUrl"]!.TrimEnd('/')}/api/auth/external/{impl.Name}/callback";

    private string UiUrl(string path) =>
        $"{_config["App:UiUrl"]!.TrimEnd('/')}{path}";

    private int? CurrentUserId() =>
        int.TryParse(User.FindFirstValue(ClaimTypes.NameIdentifier), out var id) ? id : null;

    public class TicketRequest
    {
        public string? Ticket { get; set; }
    }
}
