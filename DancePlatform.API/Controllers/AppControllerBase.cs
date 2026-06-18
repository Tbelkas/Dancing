using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

public abstract class AppControllerBase : ControllerBase
{
    protected int? CurrentUserId =>
        User.FindFirstValue(ClaimTypes.NameIdentifier) is string id ? int.Parse(id) : null;
}
