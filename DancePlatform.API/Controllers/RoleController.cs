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
        var isAdmin = await _roleService.IsAdminAsync(CurrentUserId!.Value);
        return Ok(new { isAdmin });
    }
}
