using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace DancePlatform.API.Filters;

/// <summary>Requires the caller to present a JWT whose signed isAdmin claim is "true".</summary>
[AttributeUsage(AttributeTargets.Method | AttributeTargets.Class)]
public class RequireAdminAttribute : Attribute, IAsyncActionFilter
{
    public async Task OnActionExecutionAsync(ActionExecutingContext context, ActionExecutionDelegate next)
    {
        var user = context.HttpContext.User;
        if (user.Identity?.IsAuthenticated != true)
        {
            context.Result = new UnauthorizedResult();
            return;
        }

        // Admin lives in the signed token (AuthService stamps it at login). Tokens issued
        // before that claim existed simply lack it and read as non-admin — the user re-logs
        // in to get a claim-bearing token.
        if (user.FindFirstValue("isAdmin") != "true")
        {
            context.Result = new ForbidResult();
            return;
        }

        await next();
    }
}
