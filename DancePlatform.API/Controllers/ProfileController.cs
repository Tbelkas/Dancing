using DancePlatform.API.DTOs.User;
using DancePlatform.API.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace DancePlatform.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Authorize]
public class ProfileController : AppControllerBase
{
    private readonly IUserService _userService;

    public ProfileController(IUserService userService) => _userService = userService;

    [HttpGet]
    public async Task<IActionResult> GetProfile()
    {
        var profile = await _userService.GetProfileAsync(CurrentUserId!.Value);
        return profile is null ? NotFound() : Ok(profile);
    }

    [HttpPut]
    public async Task<IActionResult> UpdateProfile([FromBody] UpdateProfileRequest request)
    {
        var profile = await _userService.UpdateProfileAsync(CurrentUserId!.Value, request);
        return profile is null ? NotFound() : Ok(profile);
    }

    [HttpPut("email")]
    public async Task<IActionResult> SetEmail([FromBody] SetEmailRequest request)
    {
        var (result, profile) = await _userService.SetEmailAsync(CurrentUserId!.Value, request.Email);
        return result switch
        {
            EmailChangeResult.UserNotFound => NotFound(),
            EmailChangeResult.AlreadyTaken =>
                Conflict(new { message = "That email address already belongs to another account." }),
            _ => Ok(profile)
        };
    }

    [HttpGet("my-dances")]
    public async Task<IActionResult> GetMyDances() =>
        Ok(await _userService.GetMyDancesAsync(CurrentUserId!.Value));
}
