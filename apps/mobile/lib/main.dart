import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const WeatherGPTApp());

class WeatherGPTApp extends StatelessWidget {
  const WeatherGPTApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WeatherGPT',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF1F5FAF), useMaterial3: true),
      home: const ChatPage(),
    );
  }
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});
  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final input = TextEditingController();
  final messages = <String>[];
  String city = 'Mysuru';
  bool loading = false;

  // Android emulator: use 10.0.2.2; iOS simulator/web: localhost.
  String get baseUrl => const String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');

  Future<void> send() async {
    final q = input.text.trim();
    if (q.isEmpty || loading) return;
    setState(() { messages.add('You: $q'); loading = true; input.clear(); });
    try {
      final r = await http.post(
        Uri.parse('$baseUrl/v1/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'message': q, 'city': city, 'language': 'en', 'latitude': 12.2958, 'longitude': 76.6394}),
      );
      final d = jsonDecode(r.body);
      setState(() => messages.add('WeatherGPT: ${d['answer']}'));
    } catch (e) {
      setState(() => messages.add('WeatherGPT: Could not reach the API. Start FastAPI on port 8000.'));
    } finally {
      setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('WeatherGPT'), actions: [
        DropdownButton<String>(value: city, items: const ['Mysuru','Pune','Mumbai','Delhi','Bengaluru']
          .map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
          onChanged: (x) => setState(() => city = x!)),
      ]),
      body: Column(children: [
        Expanded(child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: messages.length,
          itemBuilder: (_, i) => Card(child: Padding(padding: const EdgeInsets.all(14), child: Text(messages[i]))),
        )),
        Padding(padding: const EdgeInsets.all(12), child: Row(children: [
          Expanded(child: TextField(controller: input, onSubmitted: (_) => send(), decoration: const InputDecoration(hintText: 'Ask about the weather…'))),
          IconButton(onPressed: send, icon: const Icon(Icons.send)),
        ])),
      ]),
    );
  }
}
