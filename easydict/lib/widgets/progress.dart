import 'package:flutter/material.dart';

class ProgressWidget extends StatelessWidget {
  final int _complete;
  final int _pending;
  ProgressWidget(this._complete, this._pending, {Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.only(top: 4, bottom: 2),
      child: Wrap(
        spacing: 4,
        runSpacing: 4,
        children: <Widget>[
          for (int item = 0; item < _complete; item++)
            Container(
              color: Colors.amber,
              height: 4,
              width: 20,
            ),
          for (int item = 0; item < _pending; item++)
            Container(
              color: Colors.grey.shade300,
              height: 5,
              width: 20,
            ),
        ],
      ),
    );
  }
}
