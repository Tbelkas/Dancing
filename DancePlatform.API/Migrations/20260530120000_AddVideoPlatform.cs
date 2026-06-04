using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddVideoPlatform : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.RenameColumn(
                name: "YouTubeId",
                table: "Videos",
                newName: "VideoId");

            migrationBuilder.AddColumn<string>(
                name: "Platform",
                table: "Videos",
                type: "text",
                nullable: false,
                defaultValue: "youtube");

        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(name: "Platform", table: "Videos");

            migrationBuilder.RenameColumn(
                name: "VideoId",
                table: "Videos",
                newName: "YouTubeId");
        }
    }
}
