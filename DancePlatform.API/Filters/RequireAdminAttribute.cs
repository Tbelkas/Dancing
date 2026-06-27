using System.Security.Claims;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace DancePlatform.API.Filters;

/// <summary>Requires the caller to be authenticated and to have IsAdmin = true.</summary>
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

        var userIdStr = user.FindFirstValue(ClaimTypes.NameIdentifier);
        if (!int.TryParse(userIdStr, out var userId))
        {
            context.Result = new ForbidResult();
            return;
        }

        // Trust the signed isAdmin claim. Tokens issued before admin was carried in the
        // JWT lack the claim, so fall back to the DB for those until the user re-logs in.
        var adminClaim = user.FindFirstValue("isAdmin");
        var isAdmin = adminClaim is not null
            ? adminClaim == "true"
            : await context.HttpContext.RequestServices.GetRequiredService<IRoleService>().IsAdminAsync(userId);
        if (!isAdmin)
        {
            context.Result = new ForbidResult();
            return;
        }

        await next();
    }
}
