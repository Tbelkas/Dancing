using DancePlatform.API.Services;
using Xunit;

namespace DancePlatform.Tests;

public class SlugGeneratorTests
{
    [Theory]
    [InlineData("House Dance", "house-dance")]
    [InlineData("  Café Crème  ", "cafe-creme")]      // diacritics stripped, leading/trailing trimmed
    [InlineData("Reebok!!!", "reebok")]               // trailing punctuation collapsed
    [InlineData("A/B & C", "a-b-c")]                  // runs of non-alphanumerics collapse to one dash
    [InlineData("Already-Slugged", "already-slugged")]
    [InlineData("", "dance")]                          // empty falls back to "dance"
    [InlineData("   ", "dance")]
    [InlineData("!!!", "dance")]
    public void Slugify_NormalizesNames(string input, string expected) =>
        Assert.Equal(expected, SlugGenerator.Slugify(input));
}
