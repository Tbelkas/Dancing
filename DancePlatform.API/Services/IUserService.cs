using DancePlatform.API.DTOs.User;

namespace DancePlatform.API.Services;

public enum EmailChangeResult { Ok, UserNotFound, AlreadyTaken }

public enum DeleteAccountResult { Ok, UserNotFound, WrongPassword }

public interface IUserService
{
    Task<UserProfileDto?> GetProfileAsync(int userId);
    Task<UserProfileDto?> UpdateProfileAsync(int userId, UpdateProfileRequest request);
    /// <summary>Sets (or replaces) the address the account can be recovered at. Its own
    /// endpoint rather than a field on the profile update, because it is the only one that
    /// can fail on a conflict with another account.</summary>
    Task<(EmailChangeResult Result, UserProfileDto? Profile)> SetEmailAsync(int userId, string email);

    /// <summary>
    /// Erases the account and everything personal hanging off it. Requires the account's own
    /// password (a signed-in session isn't enough — a borrowed laptop shouldn't be able to do
    /// this), except for accounts that have no password because they only ever signed in
    /// through a provider.
    /// </summary>
    Task<DeleteAccountResult> DeleteAccountAsync(int userId, string password);

    Task<List<MyStyleWithDancesDto>> GetMyDancesAsync(int userId);
    Task<PublicProfileDto?> GetPublicProfileAsync(string username);
}
