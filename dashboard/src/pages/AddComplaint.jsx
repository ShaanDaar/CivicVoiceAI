/**
 * AddComplaint.jsx — Modal/overlay for citizens to file a new complaint.
 *
 * Pre-fills:
 *   - Ward from user's profile (not editable — citizen can only file for their ward)
 *   - Locality from user's locality_description
 *
 * Flow:
 *   1. User types complaint text (text mode)
 *   2. Submit → POST /classify with JWT → get category, urgency, department
 *   3. → POST /complaints with JWT → complaint saved and linked to user
 *   4. onSuccess() callback called → parent refreshes complaint list
 *
 * Props:
 *   onClose()   — close the modal
 *   onSuccess() — called after a complaint is successfully filed
 *   wardId      — the user's ward_id (pre-filled)
 *   wardName    — display name for the ward
 *   locality    — user's locality_description (pre-filled)
 */

import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { X, Send, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";

import { API_BASE } from "../config";

export default function AddComplaint({ onClose, onSuccess, wardId, wardName, locality }) {
  const { token } = useAuth();

  const [text, setText] = useState("");
  const [locationNote, setLocationNote] = useState(locality || "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null); // classification result shown after success

  // Social media draft state variables
  const [socialDraft, setSocialDraft] = useState("");
  const [loadingDraft, setLoadingDraft] = useState(false);
  const [copiedDraft, setCopiedDraft] = useState(false);
  const [draftError, setDraftError] = useState("");

  const handleGenerateSocialDraft = async () => {
    if (!result) return;
    setLoadingDraft(true);
    setDraftError("");
    setCopiedDraft(false);
    try {
      const response = await fetch(`${API_BASE}/complaints/social-draft`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          text: result.text,
          category: result.category,
          location: result.location,
          has_media: result.has_media,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to generate social draft.");
      }

      const data = await response.json();
      setSocialDraft(data.draft);
    } catch (err) {
      console.error(err);
      setDraftError(err.message || "Failed to generate social draft from server.");
    } finally {
      setLoadingDraft(false);
    }
  };

  const handleCopyDraft = () => {
    navigator.clipboard.writeText(socialDraft);
    setCopiedDraft(true);
    setTimeout(() => setCopiedDraft(false), 2000);
  };

  // Speak-mode state variables
  const [mode, setMode] = useState("type"); // "type" or "speak"
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [originalTranscript, setOriginalTranscript] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [originalLanguage, setOriginalLanguage] = useState("English");
  const [transcriptionSuccess, setTranscriptionSuccess] = useState(true);
  const [analyzingSpeech, setAnalyzingSpeech] = useState(false);

  // Media attachments state variables
  const [attachments, setAttachments] = useState([]);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [mediaError, setMediaError] = useState("");

  const handleMediaChange = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    setMediaError("");
    setUploadingMedia(true);

    for (const file of files) {
      if (!file.type.startsWith("image/") && !file.type.startsWith("video/")) {
        setMediaError("Unsupported file type. Please upload images or videos only.");
        continue;
      }
      if (file.size > 10 * 1024 * 1024) {
        setMediaError(`File '${file.name}' exceeds the 10MB maximum size limit.`);
        continue;
      }

      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_BASE}/complaints/upload`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "Upload failed.");
        }

        const data = await response.json();
        setAttachments(prev => [...prev, { url: data.url, type: data.type }]);
      } catch (err) {
        console.error("Upload error:", err);
        setMediaError(err.message || "Failed to upload file to server.");
      }
    }
    setUploadingMedia(false);
  };

  const handleRemoveAttachment = (idx) => {
    setAttachments(prev => prev.filter((_, i) => i !== idx));
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = { mimeType: "audio/webm" };
      let recorder;
      try {
        recorder = new MediaRecorder(stream, options);
      } catch (e) {
        recorder = new MediaRecorder(stream);
      }

      const chunks = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        const audioBlob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        await handleAudioUpload(audioBlob);
      };

      setMediaRecorder(recorder);
      recorder.start();
      setIsRecording(true);
      setError("");
      setOriginalTranscript("");
      setTranslatedText("");
      setOriginalLanguage("English");
      setTranscriptionSuccess(true);
    } catch (err) {
      console.error("Microphone initialization failed:", err);
      setError("Microphone access denied or not supported. Please check browser permissions or type the issue.");
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleAudioUpload = async (audioBlob) => {
    setAnalyzingSpeech(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "recorded_complaint.webm");

      const response = await fetch(`${API_BASE}/transcribe`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Voice transcription request returned a server error.");
      }

      const data = await response.json();
      if (data.transcription_success) {
        setOriginalTranscript(data.original_transcription || "");
        setTranslatedText(data.english_translation || "");
        setOriginalLanguage(data.originalLanguage || "English");
        setTranscriptionSuccess(true);
      } else {
        setOriginalTranscript("");
        setTranslatedText("Fallback: Audio transcription failed. Queued for manual triage.");
        setOriginalLanguage("Unknown");
        setTranscriptionSuccess(false);
        setError("AI could not transcribe this audio. It will default to manual review fallback on submit.");
      }
    } catch (err) {
      console.error(err);
      setOriginalTranscript("");
      setTranslatedText("Fallback: Audio transcription failed. Queued for manual triage.");
      setOriginalLanguage("Unknown");
      setTranscriptionSuccess(false);
      setError("Audio upload failed. System will process this as a manual review ticket on submit.");
    } finally {
      setAnalyzingSpeech(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Resolve parameters depending on Mode
    let finalRawInput = text;
    let finalOriginalTranscript = null;
    let finalTranslatedText = text;
    let finalOriginalLanguage = "English";
    let finalTranscriptionSuccess = true;

    if (mode === "speak") {
      finalRawInput = originalTranscript || translatedText;
      finalOriginalTranscript = originalTranscript || null;
      finalTranslatedText = translatedText;
      finalOriginalLanguage = originalLanguage || "Unknown";
      finalTranscriptionSuccess = transcriptionSuccess;
    }

    if (!finalRawInput.trim()) return;
    setSubmitting(true);
    setError("");

    try {
      // Step 1: Classify on the translated English text to resolve category/urgency/routing
      const classRes = await fetch(`${API_BASE}/classify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          raw_input: finalTranslatedText,
          ward_id: wardId,
          transcription_success: finalTranscriptionSuccess,
          originalLanguage: finalOriginalLanguage,
        }),
      });

      if (!classRes.ok) {
        const err = await classRes.json();
        throw new Error(err.detail || "Classification failed.");
      }
      const classification = await classRes.json();

      // Step 2: Persist complaint (JWT in header links it to the user)
      const complaintRes = await fetch(`${API_BASE}/complaints`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          raw_input: classification.translatedText || finalTranslatedText,
          original_transcription: finalOriginalTranscript || (mode === "type" && classification.originalLanguage !== "English" ? text : null),
          originalLanguage: classification.originalLanguage || "English",
          complaintType: classification.complaintType,
          translatedText: classification.translatedText || finalTranslatedText,
          mediaAttachments: attachments,
          urgency_score: classification.urgency_score,
          classification_method: classification.classification_method,
          location_description: locationNote || wardName,
          ward_id: wardId,
          department_id: classification.department_id,
          transcription_success: finalTranscriptionSuccess,
        }),
      });

      if (!complaintRes.ok) {
        const err = await complaintRes.json();
        throw new Error(err.detail || "Failed to save complaint.");
      }

      const createdComplaint = await complaintRes.json();

      setResult({
        category: classification.complaintType,
        urgency: classification.urgency_score,
        department: classification.department_name,
        reasoning: classification.reasoning,
        text: classification.translatedText || finalTranslatedText,
        location: locationNote || wardName,
        has_media: attachments.length > 0,
        portal_name: createdComplaint.portal_name,
        portal_url: createdComplaint.portal_url,
        portal_status: createdComplaint.portal_status,
        portal_citation: createdComplaint.portal_citation,
      });

    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    // ── Success view ──
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-card card" onClick={e => e.stopPropagation()}>
          <div className="modal-success-icon">
            <CheckCircle2 size={48} color="var(--color-success)" />
          </div>
          <h2 className="modal-title">Complaint Registered!</h2>
          <div className="modal-result-grid">
            <div className="modal-result-item">
              <span className="meta-label">Issue Type</span>
              <span className="badge badge-category">{result.category}</span>
            </div>
            <div className="modal-result-item">
              <span className="meta-label">Urgency</span>
              <span className={`badge ${result.urgency >= 4 ? "badge-urgency-high" : result.urgency >= 3 ? "badge-urgency-mid" : "badge-urgency-low"}`}>
                {result.urgency}/5
              </span>
            </div>
            <div className="modal-result-item">
              <span className="meta-label">Routed To</span>
              <span className="badge badge-method-llm">{result.department}</span>
            </div>
          </div>
          <p className="modal-reasoning"><em>{result.reasoning}</em></p>

          {/* Guided Grievance Portal Lookup Section (Citizen Success Only) */}
          {result.portal_name && (
            <div 
              className={`ticket-portal-dispatch ${result.portal_status === "Inferred" ? "portal-inferred" : "portal-verified"}`}
              style={{ marginTop: "16px", textAlign: "left", width: "100%" }}
            >
              <span className="portal-label">Official Grievance Registration Link:</span>
              <a
                href={result.portal_url}
                target="_blank"
                rel="noreferrer"
                className="portal-link"
                style={{ display: "block", marginTop: "4px", fontSize: "14px", fontWeight: "600" }}
              >
                {result.portal_status === "Inferred" ? "⚠️ " : "🔗 "}
                {result.portal_name}
              </a>
              {result.portal_status === "Inferred" ? (
                <div className="portal-disclaimer-text" style={{ marginTop: "6px", fontSize: "12px" }}>
                  <strong>Guidance:</strong> {result.portal_citation || "Inferred fallback portal; not directly verified."}
                </div>
              ) : (
                <div className="portal-verified-text" style={{ marginTop: "6px", fontSize: "12px" }}>
                  <strong>Verification Details:</strong> {result.portal_citation || "Direct official portal citation."}
                </div>
              )}
              <div className="portal-general-guidance" style={{ marginTop: "6px", fontSize: "11px", opacity: 0.8 }}>
                Note: Portal details are provided as a guide and may change; please confirm on the official site before filing.
              </div>
            </div>
          )}
          
          {/* Social Draft UI Section */}
          <div style={{
            marginTop: "16px",
            padding: "12px",
            background: "rgba(0, 0, 0, 0.02)",
            border: "1px solid var(--border-color)",
            borderRadius: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "8px"
          }}>
            {!socialDraft && !loadingDraft && !draftError && (
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={handleGenerateSocialDraft}
                style={{ width: "100%", fontSize: "13px" }}
              >
                📢 Generate Social Media Draft
              </button>
            )}

            {loadingDraft && (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", padding: "8px 0" }}>
                <RefreshCw size={14} className="spinner-icon" />
                <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Drafting post...</span>
              </div>
            )}

            {draftError && (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <p style={{ color: "var(--color-danger)", fontSize: "12px", margin: 0 }}>⚠️ {draftError}</p>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={handleGenerateSocialDraft}
                  style={{ width: "100%", fontSize: "12px" }}
                >
                  Retry Generating Draft
                </button>
              </div>
            )}

            {socialDraft && (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <label style={{ fontSize: "11px", fontWeight: "600", color: "var(--color-primary)", textTransform: "uppercase" }}>
                  Fictional Social Post (Alert)
                </label>
                <textarea
                  readOnly
                  value={socialDraft}
                  rows={3}
                  style={{
                    width: "100%",
                    background: "rgba(0, 0, 0, 0.05)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    padding: "8px",
                    fontSize: "13px",
                    color: "var(--text-primary)",
                    resize: "none"
                  }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: socialDraft.length > 280 ? "var(--color-danger)" : "var(--text-muted)" }}>
                    {socialDraft.length} / 280 characters
                  </span>
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={handleCopyDraft}
                    style={{ padding: "4px 10px", fontSize: "12px" }}
                  >
                    {copiedDraft ? "✓ Copied" : "📋 Copy Draft"}
                  </button>
                </div>
              </div>
            )}
          </div>

          <button className="btn btn-primary" style={{ width: "100%", marginTop: "16px" }} onClick={() => { onSuccess(); onClose(); }}>
            Done — View My Complaints
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card card" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2 className="modal-title">Report an Issue</h2>
          <button className="modal-close-btn" onClick={onClose}><X size={20} /></button>
        </div>
        <p className="modal-sub">
          Filing for <strong>{wardName}</strong> · AI will classify and route your complaint automatically.
        </p>

        <style>{`
          @keyframes pulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(198, 40, 40, 0.4); }
            70% { transform: scale(1.08); box-shadow: 0 0 0 10px rgba(198, 40, 40, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(198, 40, 40, 0); }
          }
          .modal-tab-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 8px 16px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
          }
          .modal-tab-btn.active {
            color: var(--color-primary, #1565C0);
            border-bottom: 2px solid var(--color-primary, #1565C0);
          }
        `}</style>

        {/* Tab selection */}
        <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.1)", marginBottom: "16px" }}>
          <button
            type="button"
            className={`modal-tab-btn ${mode === "type" ? "active" : ""}`}
            onClick={() => setMode("type")}
          >
            ✏️ Type Description
          </button>
          <button
            type="button"
            className={`modal-tab-btn ${mode === "speak" ? "active" : ""}`}
            onClick={() => setMode("speak")}
          >
            🎙️ Speak Voice
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === "type" ? (
            <div className="auth-field">
              <label htmlFor="complaint-text">Describe the issue *</label>
              <textarea
                id="complaint-text"
                rows={4}
                placeholder="e.g. The water supply pipe near the main road has been leaking for 3 days…"
                value={text}
                onChange={e => setText(e.target.value)}
                required
                style={{ resize: "vertical", minHeight: "100px" }}
              />
            </div>
          ) : (
            <div className="auth-field speak-field" style={{ padding: "8px 0" }}>
              <label style={{ display: "block", marginBottom: "8px", fontWeight: 600 }}>Speak your complaint *</label>
              
              {!originalTranscript && !translatedText && !isRecording && !analyzingSpeech && (
                <div style={{ padding: "24px", background: "rgba(255,255,255,0.03)", borderRadius: "8px", border: "1px dashed rgba(255,255,255,0.1)", textAlign: "center" }}>
                  <button
                    type="button"
                    onClick={startRecording}
                    style={{
                      background: "var(--color-primary, #1565C0)",
                      border: "none",
                      color: "#fff",
                      width: "64px",
                      height: "64px",
                      borderRadius: "50%",
                      fontSize: "24px",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      margin: "0 auto 12px",
                      boxShadow: "0 4px 10px rgba(0,0,0,0.3)"
                    }}
                  >
                    🎙️
                  </button>
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted)" }}>
                    Click mic to start recording. Speak clearly in Hindi, Marathi, Kannada, English, or any local dialect.
                  </p>
                </div>
              )}

              {isRecording && (
                <div style={{ padding: "24px", background: "rgba(198,40,40,0.05)", borderRadius: "8px", border: "1px dashed rgba(198,40,40,0.2)", textAlign: "center" }}>
                  <button
                    type="button"
                    onClick={stopRecording}
                    className="pulse-mic"
                    style={{
                      background: "#C62828",
                      color: "#fff",
                      width: "64px",
                      height: "64px",
                      borderRadius: "50%",
                      fontSize: "24px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      margin: "0 auto 12px",
                      border: "none",
                      cursor: "pointer",
                      animation: "pulse 1.5s infinite",
                    }}
                  >
                    ⏹️
                  </button>
                  <p style={{ margin: 0, fontSize: "13px", color: "#EF5350", fontWeight: 600 }}>
                    Recording... Click square button to stop recording.
                  </p>
                </div>
              )}

              {analyzingSpeech && (
                <div style={{ padding: "24px", background: "rgba(255,255,255,0.03)", borderRadius: "8px", border: "1px dashed rgba(255,255,255,0.1)", textAlign: "center" }}>
                  <RefreshCw size={24} className="spinner-icon" style={{ margin: "0 auto 12px" }} />
                  <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted)" }}>
                    Processing audio stream, transcribing and translating...
                  </p>
                </div>
              )}

              {(originalTranscript || translatedText) && !isRecording && !analyzingSpeech && (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {originalTranscript && (
                    <div className="auth-field">
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                        <label style={{ margin: 0, fontSize: "12px", color: "var(--text-muted)" }}>Original Transcript</label>
                        {originalLanguage && (
                          <span className="badge badge-language" style={{ fontSize: "10px", padding: "1px 6px" }}>
                            Language: {originalLanguage}
                          </span>
                        )}
                      </div>
                      <textarea
                        rows={3}
                        value={originalTranscript}
                        onChange={e => setOriginalTranscript(e.target.value)}
                        style={{ resize: "vertical", minHeight: "80px", width: "100%" }}
                      />
                    </div>
                  )}

                  <div className="auth-field">
                    <label style={{ display: "block", fontSize: "12px", color: "var(--color-success)", marginBottom: "4px" }}>Translated to English Preview</label>
                    <textarea
                      rows={3}
                      value={translatedText}
                      onChange={e => setTranslatedText(e.target.value)}
                      style={{ resize: "vertical", minHeight: "80px", width: "100%" }}
                      required
                    />
                  </div>

                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={startRecording}
                    style={{ alignSelf: "flex-end", padding: "4px 10px", fontSize: "12px" }}
                  >
                    🎙️ Record Again
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="auth-field">
            <label htmlFor="complaint-location">Specific location / landmark</label>
            <input
              id="complaint-location"
              type="text"
              placeholder="e.g. Near Gate 3, opposite school"
              value={locationNote}
              onChange={e => setLocationNote(e.target.value)}
            />
          </div>

          <div className="auth-field" style={{ marginTop: "12px" }}>
            <label style={{ fontWeight: 600 }}>Attachments (Images or Videos)</label>
            
            <input
              type="file"
              accept="image/*,video/*"
              multiple
              onChange={handleMediaChange}
              disabled={uploadingMedia}
              style={{ display: "none" }}
              id="media-file-input"
            />
            
            <div style={{ display: "flex", gap: "10px", alignItems: "center", marginTop: "4px" }}>
              <label
                htmlFor="media-file-input"
                className="btn btn-outline btn-sm"
                style={{
                  cursor: uploadingMedia ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  margin: 0
                }}
              >
                {uploadingMedia ? (
                  <><RefreshCw size={14} className="spinner-icon" /> Uploading...</>
                ) : (
                  <>📎 Add Photos/Videos</>
                )}
              </label>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Max 10MB per file
              </span>
            </div>

            {mediaError && (
              <p style={{ color: "#EF5350", fontSize: "12px", marginTop: "4px", marginBottom: 0 }}>
                ⚠️ {mediaError}
              </p>
            )}

            {attachments.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginTop: "10px" }}>
                {attachments.map((att, index) => (
                  <div
                    key={index}
                    style={{
                      position: "relative",
                      width: "64px",
                      height: "64px",
                      borderRadius: "6px",
                      border: "1px solid rgba(0,0,0,0.1)",
                      overflow: "hidden",
                      background: "#000"
                    }}
                  >
                    {att.type === "image" ? (
                      <img
                        src={att.url}
                        alt="attachment"
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                      />
                    ) : (
                      <video
                        src={att.url}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        preload="metadata"
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => handleRemoveAttachment(index)}
                      style={{
                        position: "absolute",
                        top: "2px",
                        right: "2px",
                        background: "rgba(0,0,0,0.6)",
                        border: "none",
                        color: "#fff",
                        borderRadius: "50%",
                        width: "16px",
                        height: "16px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "10px",
                        cursor: "pointer",
                        padding: 0
                      }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div className="auth-error">
              <AlertTriangle size={14} /> {error}
            </div>
          )}

          <div className="modal-actions">
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={
                submitting || 
                analyzingSpeech || 
                (mode === "type" && !text.trim()) || 
                (mode === "speak" && !translatedText.trim())
              }
            >
              {submitting ? (
                <><RefreshCw size={15} className="spinner-icon" /> Classifying…</>
              ) : (
                <><Send size={15} /> Submit Complaint</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
