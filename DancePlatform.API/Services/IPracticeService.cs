using DancePlatform.API.DTOs.Practice;

namespace DancePlatform.API.Services;

public interface IPracticeService
{
    Task<List<PracticeSessionDto>> GetAsync(int userId);
    Task<PracticeSessionDto?> CreateAsync(int userId, CreatePracticeSessionRequest request);
    Task<bool> DeleteAsync(int userId, int id);
}
