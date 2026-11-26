use crate::types::*;

/// All 5 Visions (OATH-232..OATH-236):
/// - 232 Conspiracy: When Played handled in `major_actions::resolve_conspiracy`.
/// - 233 Vision of Faith: Wake win check in `win::meets_vision_goal`.
/// - 234 Vision of Rebellion: Wake win check in `win::meets_vision_goal`.
/// - 235 Vision of Sanctuary: Wake win check in `win::meets_vision_goal`.
/// - 236 Vision of Conquest: Wake win check in `win::meets_vision_goal`.
pub const ALL_VISIONS: [CardId; 5] = [
    CARD_CONSPIRACY,
    CARD_VISION_FAITH,
    CARD_VISION_REBELLION,
    CARD_VISION_SANCTUARY,
    CARD_VISION_CONQUEST,
];
