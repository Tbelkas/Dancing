using DancePlatform.API.Services;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _userService;

    public UsersController(IUserService userService) => _userService = userService;

    [HttpGet("{username}")]
    public async Task<IActionResult> GetPublicProfile(string username)
    {
        var profile = await _userService.GetPublicProfileAsync(username);
        return profile is null ? NotFound() : Ok(profile);
    }
}
