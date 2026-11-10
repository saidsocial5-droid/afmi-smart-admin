using System;

namespace AFMI_Gestion_projet.Models
{
    public class AiSettings
    {
        public int Id { get; set; }
        public bool UseOllama { get; set; }
        public string OllamaEndpoint { get; set; } = "http://localhost:11434";
        public string OllamaModel { get; set; } = "mistral";
        
        // Cloud API Integration
        public bool UseCloudApi { get; set; } = false;
        public string CloudProvider { get; set; } = "OpenAI"; // "OpenAI" or "Gemini"
        public string CloudApiKey { get; set; } = string.Empty;
    }
}
