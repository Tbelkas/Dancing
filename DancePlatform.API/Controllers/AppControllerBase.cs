using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

public abstract class AppControllerBase : ControllerBase
{
    // TryParse (not Parse): a malformed/absent NameIdentifier claim yields null (treat as anonymous)
    // rather than throwing and turning every request under a tampered token into a 500.
    protected int? CurrentUserId =>
        int.TryParse(User.FindFirstValue(ClaimTypes.NameIdentifier), out var id) ? id : null;

    // The signed isAdmin claim stamped at login (see RequireAdminAttribute / AuthService).
    protected bool CurrentUserIsAdmin => User.FindFirstValue("isAdmin") == "true";
}
