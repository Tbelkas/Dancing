using System.Security.Claims;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class RoleController : AppControllerBase
{
    private readonly IRoleService _roleService;

    public RoleController(IRoleService roleService) => _roleService = roleService;

    [Authorize]
    [HttpGet("me")]
    public async Task<IActionResult> GetMyRole()
    {
        // Prefer the signed claim; fall back to the DB for legacy tokens that predate it.
        var adminClaim = User.FindFirstValue("isAdmin");
        var isAdmin = adminClaim is not null
            ? adminClaim == "true"
            : await _roleService.IsAdminAsync(CurrentUserId!.Value);
        return Ok(new { isAdmin });
    }
}
