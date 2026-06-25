using System.Globalization;
using System.Text;
using DancePlatform.API.Models;

namespace DancePlatform.API.Services;

public static class SlugGenerator
{
    /// <summary>
    /// The slug of a dance's canonical (primary) style — the lowest-StyleId style it belongs to.
    /// Used to build the /dances/{style}/{slug} URL. Returns "" if the dance has no style.
    /// Ordering by StyleId keeps the choice deterministic across endpoints.
    /// </summary>
    public static string StyleSlug(Dance dance)
    {
        var style = dance.DanceStyles.OrderBy(ds => ds.StyleId).Select(ds => ds.Style).FirstOrDefault();
        return style is null ? string.Empty : Slugify(style.Name);
    }

    /// <summary>Converts a name to a URL slug: lowercase, diacritics stripped, non-alphanumerics collapsed to '-'.</summary>
    public static string Slugify(string name)
    {
        var normalized = name.Normalize(NormalizationForm.FormD);
        var sb = new StringBuilder(normalized.Length);
        var lastWasDash = true; // suppress leading dashes

        foreach (var c in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) == UnicodeCategory.NonSpacingMark) continue;
            if (char.IsAsciiLetterOrDigit(c))
            {
                sb.Append(char.ToLowerInvariant(c));
                lastWasDash = false;
            }
            else if (!lastWasDash)
            {
                sb.Append('-');
                lastWasDash = true;
            }
        }

        var slug = sb.ToString().TrimEnd('-');
        return slug.Length > 0 ? slug : "dance";
    }
}
