using System.Security.Claims;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;

namespace DancePlatform.API.Filters;

/// <summary>
/// Requires the caller to be authenticated and to have IsAdmin = true.
/// JWT transition: update IRoleService implementation to read the "IsAdmin"
/// claim from the token instead of querying the database.
/// </summary>
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

        var roleService = context.HttpContext.RequestServices.GetRequiredService<IRoleService>();
        if (!await roleService.IsAdminAsync(userId))
        {
            context.Result = new ForbidResult();
            return;
        }

        await next();
    }
}
