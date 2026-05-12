using DancePlatform.API.DTOs.User;

namespace DancePlatform.API.Services;

public interface IUserService
{
    Task<UserProfileDto?> GetProfileAsync(int userId);
    Task<UserProfileDto?> UpdateProfileAsync(int userId, UpdateProfileRequest request);
    Task<List<MyStyleWithDancesDto>> GetMyDancesAsync(int userId);
}
