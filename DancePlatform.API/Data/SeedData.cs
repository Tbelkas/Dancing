using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Data;

public static class SeedData
{
    public static async Task SeedAsync(AppDbContext db)
    {
        if (await db.Dances.AnyAsync()) return;

        // --- Styles ---
        var latin       = new Style { Name = "Latin",              Description = "Energetic dances originating from Latin America" };
        var ballroom    = new Style { Name = "Ballroom",           Description = "Elegant partner dances performed in a ballroom" };
        var street      = new Style { Name = "Street / Urban",     Description = "Freestyle and battle dances born in urban culture" };
        var classical   = new Style { Name = "Classical / Ballet", Description = "Formal dance forms rooted in classical tradition" };
        var folk        = new Style { Name = "Folk / Traditional", Description = "Traditional dances tied to cultural heritage" };
        var swing       = new Style { Name = "Swing",              Description = "Upbeat partner dances from the swing era" };
        var contemporary = new Style { Name = "Contemporary",     Description = "Modern expressive dance blending multiple styles" };

        db.Styles.AddRange(latin, ballroom, street, classical, folk, swing, contemporary);

        // --- Musical Styles ---
        var salsaMusic     = new MusicalStyle { Name = "Salsa",                Description = "Afro-Cuban rhythm originating in New York" };
        var classicalMusic = new MusicalStyle { Name = "Classical / Orchestral", Description = "European classical music tradition" };
        var hipHop         = new MusicalStyle { Name = "Hip-Hop",              Description = "Urban music featuring beats, rap and sampling" };
        var jazz           = new MusicalStyle { Name = "Jazz",                 Description = "Improvisational American music style" };
        var tangoMusic     = new MusicalStyle { Name = "Tango",                Description = "Sensual Argentine and Uruguayan music" };
        var electronic     = new MusicalStyle { Name = "Electronic / EDM",     Description = "Electronically produced dance music" };
        var blues          = new MusicalStyle { Name = "Blues",                Description = "African-American roots music from the Deep South" };
        var reggaeton      = new MusicalStyle { Name = "Reggaeton",            Description = "Urban Latin music blending reggae and hip-hop" };
        var cumbia         = new MusicalStyle { Name = "Cumbia",               Description = "Colombian folk music with African and Indigenous roots" };
        var flamencoMusic  = new MusicalStyle { Name = "Flamenco",             Description = "Passionate Spanish Andalusian music" };

        db.MusicalStyles.AddRange(salsaMusic, classicalMusic, hipHop, jazz, tangoMusic, electronic, blues, reggaeton, cumbia, flamencoMusic);

        // --- Dances ---
        var salsa            = new Dance { Name = "Salsa",        Description = "A vibrant Latin partner dance with complex footwork and hip movements, originating in New York's Cuban community." };
        var waltz            = new Dance { Name = "Waltz",        Description = "A smooth, flowing ballroom dance in 3/4 time, characterized by its rise-and-fall motion and elegant turns." };
        var tango            = new Dance { Name = "Tango",        Description = "A passionate and dramatic partner dance from Argentina, known for its sharp movements and close embrace." };
        var breakdance       = new Dance { Name = "Breakdance",   Description = "An acrobatic street dance featuring power moves, freezes and footwork, born in the Bronx in the 1970s." };
        var ballet           = new Dance { Name = "Ballet",       Description = "A highly technical classical dance form emphasizing grace, precision and athleticism, originating in the Italian Renaissance." };
        var flamenco         = new Dance { Name = "Flamenco",     Description = "An expressive Spanish art form combining song, guitar, dance and clapping, originating in Andalusia." };
        var jive             = new Dance { Name = "Jive",         Description = "A lively ballroom dance in 4/4 time performed to swing or rock and roll music." };
        var chaCha           = new Dance { Name = "Cha-Cha",      Description = "A rhythmical Latin dance with a distinctive cha-cha-cha triple step, originating in Cuba in the 1950s." };
        var bachata          = new Dance { Name = "Bachata",      Description = "A sensual partner dance from the Dominican Republic characterized by a side-to-side hip motion." };
        var popping          = new Dance { Name = "Popping",      Description = "A street funk dance style based on quickly contracting and relaxing muscles to create a sharp pop effect." };
        var contemporaryDance = new Dance { Name = "Contemporary", Description = "An expressive genre blending ballet, jazz and modern dance that encourages personal interpretation." };
        var foxtrot          = new Dance { Name = "Foxtrot",      Description = "A smooth, progressive ballroom dance characterized by long, flowing movements and alternating slow-quick steps." };

        db.Dances.AddRange(salsa, waltz, tango, breakdance, ballet, flamenco, jive, chaCha, bachata, popping, contemporaryDance, foxtrot);

        foreach (var dance in db.Dances.Local)
            dance.Slug = Services.SlugGenerator.Slugify(dance.Name);

        await db.SaveChangesAsync();

        // --- Dance ↔ Style ---
        db.DanceStyles.AddRange(
            new DanceStyle { DanceId = salsa.Id,             StyleId = latin.Id },
            new DanceStyle { DanceId = waltz.Id,             StyleId = ballroom.Id },
            new DanceStyle { DanceId = tango.Id,             StyleId = latin.Id },
            new DanceStyle { DanceId = tango.Id,             StyleId = ballroom.Id },
            new DanceStyle { DanceId = breakdance.Id,        StyleId = street.Id },
            new DanceStyle { DanceId = ballet.Id,            StyleId = classical.Id },
            new DanceStyle { DanceId = flamenco.Id,          StyleId = folk.Id },
            new DanceStyle { DanceId = jive.Id,              StyleId = ballroom.Id },
            new DanceStyle { DanceId = jive.Id,              StyleId = swing.Id },
            new DanceStyle { DanceId = chaCha.Id,            StyleId = latin.Id },
            new DanceStyle { DanceId = bachata.Id,           StyleId = latin.Id },
            new DanceStyle { DanceId = popping.Id,           StyleId = street.Id },
            new DanceStyle { DanceId = contemporaryDance.Id, StyleId = contemporary.Id },
            new DanceStyle { DanceId = foxtrot.Id,           StyleId = ballroom.Id }
        );

        // --- Dance ↔ Musical Style ---
        db.DanceMusicalStyles.AddRange(
            new DanceMusicalStyle { DanceId = salsa.Id,             MusicalStyleId = salsaMusic.Id },
            new DanceMusicalStyle { DanceId = salsa.Id,             MusicalStyleId = reggaeton.Id },
            new DanceMusicalStyle { DanceId = waltz.Id,             MusicalStyleId = classicalMusic.Id },
            new DanceMusicalStyle { DanceId = tango.Id,             MusicalStyleId = tangoMusic.Id },
            new DanceMusicalStyle { DanceId = breakdance.Id,        MusicalStyleId = hipHop.Id },
            new DanceMusicalStyle { DanceId = breakdance.Id,        MusicalStyleId = electronic.Id },
            new DanceMusicalStyle { DanceId = ballet.Id,            MusicalStyleId = classicalMusic.Id },
            new DanceMusicalStyle { DanceId = flamenco.Id,          MusicalStyleId = flamencoMusic.Id },
            new DanceMusicalStyle { DanceId = jive.Id,              MusicalStyleId = jazz.Id },
            new DanceMusicalStyle { DanceId = jive.Id,              MusicalStyleId = blues.Id },
            new DanceMusicalStyle { DanceId = chaCha.Id,            MusicalStyleId = salsaMusic.Id },
            new DanceMusicalStyle { DanceId = chaCha.Id,            MusicalStyleId = cumbia.Id },
            new DanceMusicalStyle { DanceId = bachata.Id,           MusicalStyleId = reggaeton.Id },
            new DanceMusicalStyle { DanceId = popping.Id,           MusicalStyleId = hipHop.Id },
            new DanceMusicalStyle { DanceId = popping.Id,           MusicalStyleId = electronic.Id },
            new DanceMusicalStyle { DanceId = contemporaryDance.Id, MusicalStyleId = electronic.Id },
            new DanceMusicalStyle { DanceId = foxtrot.Id,           MusicalStyleId = jazz.Id }
        );

        // --- Videos ---
        db.Videos.AddRange(
            new Video { Title = "Salsa Basic Steps for Beginners",       VideoId ="nCGXCR4yCzk", DanceId = salsa.Id,             Description = "Learn the fundamental salsa steps and timing in this beginner-friendly tutorial." },
            new Video { Title = "Salsa On2 Timing Explained",            VideoId ="K8F8v6GCFhg", DanceId = salsa.Id,             Description = "Master the New York-style salsa on2 timing with a detailed footwork breakdown." },
            new Video { Title = "Waltz for Beginners – Basic Steps",     VideoId ="J5hBxiT-NsY", DanceId = waltz.Id,             Description = "Step-by-step guide to the natural turn, reverse turn and basic box in waltz." },
            new Video { Title = "Argentine Tango – Walking Technique",   VideoId ="dN4TT5kFvOg", DanceId = tango.Id,             Description = "Foundation of Argentine tango: the walk, posture and connection with your partner." },
            new Video { Title = "Breakdance Footwork for Beginners",     VideoId ="WC5oGldzGiQ", DanceId = breakdance.Id,        Description = "Learn the 6-step, the fundamental footwork pattern for all bboys and bgirls." },
            new Video { Title = "Ballet Barre Exercises – Beginner",     VideoId ="pLsAZhGMeaU", DanceId = ballet.Id,            Description = "A complete beginner barre workout covering pliés, tendus and dégagés." },
            new Video { Title = "Flamenco Footwork Basics – Zapateado",  VideoId ="HhVbFZGu3eE", DanceId = flamenco.Id,          Description = "Introduction to flamenco zapateado, the essential footwork technique." },
            new Video { Title = "Jive – Basic Steps Tutorial",           VideoId ="T9LchSmfK3s", DanceId = jive.Id,              Description = "Learn the jive basic steps, underarm turns and American spin." },
            new Video { Title = "Cha-Cha Basic Steps for Beginners",     VideoId ="vMGpWlxsXEY", DanceId = chaCha.Id,            Description = "Master the cha-cha basic with proper hip action and timing." },
            new Video { Title = "Bachata for Complete Beginners",        VideoId ="bLXAVMgWBME", DanceId = bachata.Id,           Description = "Learn the bachata basic step, side step and hip motion from scratch." },
            new Video { Title = "Bachata Sensual – Body Movement",       VideoId ="RP4abiHdQpc", DanceId = bachata.Id,           Description = "Explore the body waves and sensual movement of modern bachata sensual style." },
            new Video { Title = "Popping Tutorial – The Basics",         VideoId ="9bZkp7q19f0", DanceId = popping.Id,           Description = "Learn how to pop correctly: chest pop, arm pop and neck pop." },
            new Video { Title = "Contemporary Dance Technique",          VideoId ="XbpmVxnFQdk", DanceId = contemporaryDance.Id, Description = "Explore floor work, weight shifting and improvisation in contemporary dance." },
            new Video { Title = "Foxtrot Basic Steps – Ballroom",        VideoId ="Ct6BUPvE2sQ", DanceId = foxtrot.Id,           Description = "Learn the foxtrot feather step, reverse turn and three-step sequence." }
        );

        // --- Users ---
        var users = new[]
        {
            new User { Username = "maria_salsa",   PasswordHash = BCrypt.Net.BCrypt.HashPassword("Password123"), Name = "Maria González",   Nickname = "MariaG",   Visibility = ProfileVisibility.Public  },
            new User { Username = "alex_dancer",   PasswordHash = BCrypt.Net.BCrypt.HashPassword("Password123"), Name = "Alex Chen",         Nickname = "AlexC",    Visibility = ProfileVisibility.Public  },
            new User { Username = "sophie_ballet", PasswordHash = BCrypt.Net.BCrypt.HashPassword("Password123"), Name = "Sophie Dubois",     Nickname = "SophieD",  Visibility = ProfileVisibility.Public  },
            new User { Username = "carlos_tango",  PasswordHash = BCrypt.Net.BCrypt.HashPassword("Password123"), Name = "Carlos Fernández",  Nickname = "CarlosF",  Visibility = ProfileVisibility.Public  },
            new User { Username = "kira_bboy",     PasswordHash = BCrypt.Net.BCrypt.HashPassword("Password123"), Name = "Kira Johnson",      Nickname = "KiraJ",    Visibility = ProfileVisibility.Private },
        };

        db.Users.AddRange(users);
        await db.SaveChangesAsync();

        // --- User Favorites ---
        db.UserFavoriteDances.AddRange(
            new UserFavoriteDance { UserId = users[0].Id, DanceId = salsa.Id },
            new UserFavoriteDance { UserId = users[0].Id, DanceId = bachata.Id },
            new UserFavoriteDance { UserId = users[0].Id, DanceId = chaCha.Id },
            new UserFavoriteDance { UserId = users[1].Id, DanceId = breakdance.Id },
            new UserFavoriteDance { UserId = users[1].Id, DanceId = popping.Id },
            new UserFavoriteDance { UserId = users[1].Id, DanceId = contemporaryDance.Id },
            new UserFavoriteDance { UserId = users[2].Id, DanceId = ballet.Id },
            new UserFavoriteDance { UserId = users[2].Id, DanceId = contemporaryDance.Id },
            new UserFavoriteDance { UserId = users[3].Id, DanceId = tango.Id },
            new UserFavoriteDance { UserId = users[3].Id, DanceId = salsa.Id },
            new UserFavoriteDance { UserId = users[4].Id, DanceId = breakdance.Id },
            new UserFavoriteDance { UserId = users[4].Id, DanceId = popping.Id }
        );

        // --- User Learned Dances ---
        db.UserLearnedDances.AddRange(
            new UserLearnedDance { UserId = users[0].Id, DanceId = salsa.Id },
            new UserLearnedDance { UserId = users[0].Id, DanceId = chaCha.Id },
            new UserLearnedDance { UserId = users[1].Id, DanceId = breakdance.Id },
            new UserLearnedDance { UserId = users[2].Id, DanceId = ballet.Id },
            new UserLearnedDance { UserId = users[3].Id, DanceId = tango.Id },
            new UserLearnedDance { UserId = users[4].Id, DanceId = breakdance.Id },
            new UserLearnedDance { UserId = users[4].Id, DanceId = popping.Id }
        );

        await db.SaveChangesAsync();
    }
}
