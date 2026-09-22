using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddVideoChannel : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "ChannelName",
                table: "Videos",
                type: "text",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "ChannelUrl",
                table: "Videos",
                type: "text",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_Videos_ChannelName",
                table: "Videos",
                column: "ChannelName");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropIndex(
                name: "IX_Videos_ChannelName",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "ChannelName",
                table: "Videos");

            migrationBuilder.DropColumn(
                name: "ChannelUrl",
                table: "Videos");
        }
    }
}
