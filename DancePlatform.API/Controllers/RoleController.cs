using System.Security.Claims;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RoleController : ControllerBase
{
    private readonly IRoleService _roleService;

    public RoleController(IRoleService roleService) => _roleService = roleService;

    /// <summary>
    /// Returns the current user's role flags.
    /// JWT transition: when IsAdmin is embedded in the token, this endpoint
    /// can read it from claims without a DB query, or be deprecated entirely.
    /// </summary>
    [Authorize]
    [HttpGet("me")]
    public async Task<IActionResult> GetMyRole()
    {
        var userIdStr = User.FindFirstValue(ClaimTypes.NameIdentifier);
        if (!int.TryParse(userIdStr, out var userId))
            return Unauthorized();

        var isAdmin = await _roleService.IsAdminAsync(userId);
        return Ok(new { isAdmin });
    }
}
