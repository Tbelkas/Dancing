using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddDanceSlug : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "Slug",
                table: "Dances",
                type: "text",
                nullable: false,
                defaultValue: "");

            // Backfill: slugify existing names, then suffix duplicates with -2, -3, ... (oldest keeps the bare slug)
            migrationBuilder.Sql("""
                UPDATE "Dances"
                SET "Slug" = COALESCE(NULLIF(btrim(regexp_replace(lower("Name"), '[^a-z0-9]+', '-', 'g'), '-'), ''), 'dance');

                UPDATE "Dances" d
                SET "Slug" = d."Slug" || '-' || s.rn
                FROM (
                    SELECT "Id", row_number() OVER (PARTITION BY "Slug" ORDER BY "Id") AS rn
                    FROM "Dances"
                ) s
                WHERE d."Id" = s."Id" AND s.rn > 1;
                """);

            migrationBuilder.CreateIndex(
                name: "IX_Dances_Slug",
                table: "Dances",
                column: "Slug",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_Dances_Slug",
                table: "Dances");

            migrationBuilder.DropColumn(
                name: "Slug",
                table: "Dances");
        }
    }
}
